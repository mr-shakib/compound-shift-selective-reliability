"""C3-E6 Stage 6: M1 through M4, exactly as fixed by protocol v0.4.0.

Nothing here is tunable. Architecture, resolution, pooling, fusion form, and
head shape are all frozen in `models.exact_backbones`; this module is a faithful
construction of that specification, not a place to explore alternatives.

The four models are deliberately conventional. The study claims no architectural
novelty — `study_identity.not_claimed` lists it explicitly — so the backbone is
a control held constant, which is what makes any observed transport failure
attributable to the shift rather than to the model.

M1 image-only     non-multimodal control
M2 text-only      text-signal and shortcut control
M3 late fusion    averages M1 and M2 probabilities; trains nothing of its own
M4 feature fusion concatenates pooled features into a two-layer MLP
"""

from __future__ import annotations

import torch
import torch.nn as nn

N_TARGETS = 5
IMAGE_FEATURE_DIM = 1024  # densenet121 final feature width
TEXT_FEATURE_DIM = 768    # bert-base-uncased hidden size
FUSION_HIDDEN = 512


def _image_backbone(memory_efficient: bool = False) -> tuple[nn.Module, int]:
    """DenseNet-121, ImageNet-initialised, classifier stripped to features.

    `memory_efficient` switches torchvision's dense layers to checkpointed
    concatenation. It recomputes intermediate activations in the backward pass
    rather than storing them, which changes speed and memory but not the
    function computed or the weights loaded.
    """
    from torchvision.models import DenseNet121_Weights, densenet121

    net = densenet121(weights=DenseNet121_Weights.IMAGENET1K_V1,
                      memory_efficient=memory_efficient)
    net.classifier = nn.Identity()
    return net, IMAGE_FEATURE_DIM


def _text_backbone() -> tuple[nn.Module, int]:
    """BERT-base-uncased; CLS pooling is applied by the caller."""
    from transformers import BertModel

    return BertModel.from_pretrained("bert-base-uncased"), TEXT_FEATURE_DIM


class M1ImageOnly(nn.Module):
    """Image-only control. Five independent sigmoid heads over DenseNet features."""

    def __init__(self) -> None:
        super().__init__()
        self.backbone, dim = _image_backbone()
        self.head = nn.Linear(dim, N_TARGETS)

    def forward(self, image: torch.Tensor, **_: torch.Tensor) -> torch.Tensor:
        return self.head(self.backbone(image))


class M2TextOnly(nn.Module):
    """Text-only control.

    This model exists to detect shortcuts. If pre-diagnostic context alone
    predicts the label well, the multimodal models may be leaning on text rather
    than on the radiograph, and the Stage 3B leakage audit becomes load-bearing.
    """

    def __init__(self) -> None:
        super().__init__()
        self.backbone, dim = _text_backbone()
        self.head = nn.Linear(dim, N_TARGETS)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor,
                **_: torch.Tensor) -> torch.Tensor:
        out = self.backbone(input_ids=input_ids, attention_mask=attention_mask)
        cls = out.last_hidden_state[:, 0]  # CLS pooling, per the registry
        return self.head(cls)


class M3LateFusion(nn.Module):
    """Probability-average of a trained M1 and M2.

    Trains no parameters of its own, which is the point: it is the transparent
    multimodal baseline, so any gain over M1 is attributable to the text signal
    rather than to extra capacity.
    """

    def __init__(self, m1: M1ImageOnly, m2: M2TextOnly) -> None:
        super().__init__()
        self.m1 = m1
        self.m2 = m2
        for p in self.parameters():
            p.requires_grad_(False)

    def forward(self, image: torch.Tensor, input_ids: torch.Tensor,
                attention_mask: torch.Tensor, **_: torch.Tensor) -> torch.Tensor:
        p1 = torch.sigmoid(self.m1(image))
        p2 = torch.sigmoid(self.m2(input_ids=input_ids, attention_mask=attention_mask))
        p = (p1 + p2) / 2.0
        # Return logits so the loss and the selective policy see one convention.
        return torch.log(p.clamp(1e-6, 1 - 1e-6) / (1 - p).clamp(1e-6, 1 - 1e-6))


class M4FeatureFusion(nn.Module):
    """Concatenated pooled features into a two-layer MLP, trained jointly.

    Gradient checkpointing is enabled on the text encoder. M4 holds DenseNet-121
    and BERT-base resident at once, which exceeds the 6 GB hardware gate at the
    frozen batch size of 32. Checkpointing recomputes BERT activations during the
    backward pass instead of storing them: it costs time, not accuracy, and
    leaves the model, the batch size, and the optimisation settings exactly as
    the protocol fixes them. Reducing the batch size instead would have altered a
    preregistered value.
    """

    def __init__(self, gradient_checkpointing: bool = True) -> None:
        super().__init__()
        self.image_backbone, img_dim = _image_backbone(
            memory_efficient=gradient_checkpointing)
        self.text_backbone, txt_dim = _text_backbone()
        if gradient_checkpointing:
            self.text_backbone.gradient_checkpointing_enable()
        self.head = nn.Sequential(
            nn.Linear(img_dim + txt_dim, FUSION_HIDDEN),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(FUSION_HIDDEN, N_TARGETS),
        )

    def forward(self, image: torch.Tensor, input_ids: torch.Tensor,
                attention_mask: torch.Tensor, **_: torch.Tensor) -> torch.Tensor:
        img = self.image_backbone(image)
        txt = self.text_backbone(input_ids=input_ids,
                                 attention_mask=attention_mask).last_hidden_state[:, 0]
        return self.head(torch.cat([img, txt], dim=1))


def masked_bce_with_logits(logits: torch.Tensor, target: torch.Tensor,
                           mask: torch.Tensor) -> torch.Tensor:
    """Binary cross-entropy over supervised cells only.

    Uncertain and unmentioned labels carry no supervision and are excluded
    rather than mapped to negative. Mapping them would inflate the negative
    class and change the prevalence the protocol froze — for Atelectasis, where
    CheXbert emits almost no explicit negatives, it would be severe.
    """
    per_cell = nn.functional.binary_cross_entropy_with_logits(
        logits, target, reduction="none")
    denom = mask.sum().clamp(min=1.0)
    return (per_cell * mask).sum() / denom


MODEL_REGISTRY = {
    "M1": M1ImageOnly,
    "M2": M2TextOnly,
    "M4": M4FeatureFusion,
}
