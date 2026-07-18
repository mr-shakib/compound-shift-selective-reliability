#!/usr/bin/env python3
from pathlib import Path
import json, sys, yaml
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[1]; CONFIG=ROOT/'config'; SCHEMA=ROOT/'schema'; REPORTS=ROOT/'reports'
def ly(n): return yaml.safe_load((CONFIG/n).read_text(encoding='utf-8'))
def lj(n): return json.loads((SCHEMA/n).read_text(encoding='utf-8'))
def check(cond,code,msg,failures,passes): (passes if cond else failures).append({'code':code,'message':msg})
def main():
 REPORTS.mkdir(exist_ok=True); exp=ly('experiment_registry.yaml'); ctx=ly('context_interventions.yaml'); met=ly('metric_registry.yaml'); hyp=ly('hypothesis_registry.yaml'); data=ly('data_policy.yaml'); failures=[]; passes=[]
 for name,inst,sch in [('experiment_registry',exp,lj('experiment_registry.schema.json')),('context_interventions',ctx,lj('context_interventions.schema.json')),('metric_registry',met,lj('metric_registry.schema.json'))]:
  errs=sorted(Draft202012Validator(sch).iter_errors(inst),key=lambda e:list(e.path))
  if errs:
   for e in errs: failures.append({'code':'SCHEMA_'+name.upper(),'message':f'{list(e.path)}: {e.message}'})
  else: passes.append({'code':'SCHEMA_'+name.upper(),'message':name+' conforms to JSON Schema'})
 check(exp['authorization']['model_training'] is False,'AUTH_TRAINING_LOCK','Model training remains unauthorized.',failures,passes)
 check(exp['authorization']['medical_image_loading'] is False,'AUTH_IMAGE_LOCK','Medical image loading remains unauthorized.',failures,passes)
 check(exp['datasets']['external']['tuning_allowed'] is False,'TARGET_TUNING_LOCK','External-site tuning is prohibited.',failures,passes)
 check(exp['governance']['training_authorized'] is False,'GOV_TRAINING_LOCK','Governance training flag is false.',failures,passes)
 expected={'Cardiomegaly','Edema','Pleural Effusion','Atelectasis','Consolidation'}
 check(set(exp['targets']['pathologies'])==expected,'TARGET_SET','Exactly the five locked pathologies are present.',failures,passes)
 check(exp['targets']['primary_label_source']=='impression_fixed.json','LABEL_PRIMARY','Primary label source is impression_fixed.json.',failures,passes)
 check(exp['targets']['sensitivity_label_source']=='findings_fixed.json','LABEL_SENSITIVITY','Sensitivity label source is findings_fixed.json.',failures,passes)
 check(exp['targets']['forbidden_label_source']=='report_fixed.json','LABEL_FORBIDDEN','report_fixed.json is forbidden.',failures,passes)
 permitted=set(exp['text_policy']['permitted_sections_external'])|set(exp['text_policy']['permitted_sections_source']); forbidden=set(exp['text_policy']['forbidden_sections'])
 check(permitted.isdisjoint(forbidden),'TEXT_SECTION_DISJOINT','Permitted and forbidden text sections are disjoint.',failures,passes)
 check({'findings','impression','full_report'}.issubset(set(data['prohibited_columns_in_model_input'])),'DATA_INPUT_LEAKAGE','Post-diagnostic report fields are prohibited model inputs.',failures,passes)
 natural=[x['id'] for x in ctx['natural_context_states']]; controlled=[x['id'] for x in ctx['controlled_interventions']]
 check(len(natural)==len(set(natural)),'CTX_NATURAL_UNIQUE','Natural context IDs are unique.',failures,passes)
 check(set(controlled)=={'C0','C1','C2'},'CTX_CONTROLLED_SET','Controlled interventions are exactly C0, C1, C2.',failures,passes)
 c1=next(x for x in ctx['controlled_interventions'] if x['id']=='C1'); c2=next(x for x in ctx['controlled_interventions'] if x['id']=='C2'); cons=c2.get('constraints',{})
 check(c1.get('replacement_token')=='[NO_CONTEXT]','CTX_NO_CONTEXT_TOKEN','C1 uses the locked [NO_CONTEXT] token.',failures,passes)
 check(cons.get('different_patient') is True,'CTX_C2_DIFFERENT_PATIENT','C2 requires a different-patient donor.',failures,passes)
 check(cons.get('same_institution') is True and cons.get('same_split') is True,'CTX_C2_WITHIN_DOMAIN','C2 remains within institution and split.',failures,passes)
 model_ids=[m['id'] for m in exp['models']['core']]
 check(model_ids==['M1','M2','M3','M4'],'MODEL_CORE_SET','Core model set is exactly M1-M4.',failures,passes)
 check(next(m for m in exp['models']['core'] if m['id']=='M1')['modalities']==['image'],'MODEL_M1_IMAGE_ONLY','M1 is image-only.',failures,passes)
 check(exp['selective_policy']['primary_source_coverage']==0.80,'SELECTIVE_PRIMARY_COVERAGE','Primary source coverage is 80%.',failures,passes)
 check(exp['selective_policy']['frozen_threshold_transfer'] is True,'SELECTIVE_FROZEN_TRANSFER','Threshold transfer is frozen.',failures,passes)
 check(exp['statistics']['bootstrap_replicates']==2000,'STATS_BOOTSTRAP_REPS','Bootstrap replicates equal 2000.',failures,passes)
 check(exp['statistics']['bootstrap_seed']==20260718,'STATS_BOOTSTRAP_SEED','Bootstrap seed is 20260718.',failures,passes)
 check(exp['statistics']['resampling_unit']=='patient','STATS_CLUSTER_UNIT','Bootstrap resampling unit is patient.',failures,passes)
 mids=[m['id'] for m in met['metrics']]; mnames=[m['name'] for m in met['metrics']]
 check(len(mids)==len(set(mids)),'METRIC_ID_UNIQUE','Metric IDs are unique.',failures,passes)
 req={'selective_risk_at_frozen_threshold','coverage_at_frozen_threshold','risk_transport_gap','coverage_transport_gap','controlled_context_penalty','compound_shift_interaction','AUGRC'}
 check(req.issubset(set(mnames)),'METRIC_REQUIRED_SET','All locked primary metrics are registered.',failures,passes)
 badm=[h['id'] for h in hyp['hypotheses'] if h['estimand_metric_id'] not in set(mids)]; badmodels=[(h['id'],m) for h in hyp['hypotheses'] for m in h.get('models',[]) if m not in set(model_ids)]
 check(not badm,'HYP_METRIC_REFS','Every hypothesis references a registered metric.',failures,passes)
 check(not badmodels,'HYP_MODEL_REFS','Every hypothesis references a registered core model.',failures,passes)
 prohibited=set(exp['governance']['external_dataset_prohibited_uses']); required={'architecture_selection','early_stopping','temperature_selection','classification_threshold_selection','abstention_threshold_selection','model_retraining'}
 check(required.issubset(prohibited),'TARGET_PROHIBITIONS','Core target-site prohibited uses are registered.',failures,passes)
 report={'protocol_id':exp['protocol_id'],'protocol_version':exp['protocol_version'],'status':'PASS' if not failures else 'FAIL','checks_passed':len(passes),'checks_failed':len(failures),'passes':passes,'failures':failures}
 path=REPORTS/'validation_report.json'; path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'status':report['status'],'checks_passed':len(passes),'checks_failed':len(failures),'report':str(path)},indent=2)); return 0 if not failures else 1
if __name__=='__main__': raise SystemExit(main())
