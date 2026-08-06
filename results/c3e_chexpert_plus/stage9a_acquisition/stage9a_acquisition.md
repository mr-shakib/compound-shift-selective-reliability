# C3-E9a — External-Site Image Acquisition

Status: **PASS**

- **STAGE 9a ONLY**
- **EXTERNAL-SITE IMAGE ACQUISITION AND RESIZE**
- **NO EXTERNAL-SITE INFERENCE**
- **NO EXTERNAL-SITE TUNING**
- **NO THRESHOLD SELECTION**
- **NO CROSS-SITE CLAIM**
- **PREPROCESSING IDENTICAL TO THE SOURCE SITE**
- **IMAGES CONFINED TO THE PROTECTED DATA TREE**
- **NO IDENTIFIERS EMITTED TO RESULTS**

| field | value |
| --- | ---: |
| images expected | 191,071 |
| images written | 0 |
| already present | 191,070 |
| md5 mismatches | 0 |
| corrupt at source (excluded) | 1 |
| usable images | 191,070 |
| errors | 0 |
| transferred | 616 GB |
| stored at 224px | 2.82 GB |
| elapsed | 0.0 h |

Preprocessing matches the source site exactly: a single bilinear resize
from full resolution to 224px, grayscale, JPEG quality 95. Applying a
second resampling only at the external site would introduce a
preprocessing difference tracking the site variable under study.

Image paths are restricted data and are not included here.
