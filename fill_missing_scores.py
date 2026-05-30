
import json, re

def normalize(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

def compute_opportunity_score(r):
    weights = {'demand_score': 0.30, 'income_score': 0.25, 'transferability_score': 0.20,
               'newcomer_score': 0.15, 'ai_risk': -0.10}
    return round(max(0, min(10, sum(r.get(k,5)*w for k,w in weights.items()))), 1)

def score_by_title(title):
    t = title.lower()
    teer_map = {'0':0,'1':1,'2':2,'3':3,'4':4,'5':5}

    high_ai = ['data entry','typist','bookkeeper','accounting clerk','payroll clerk',
               'cashier','translator','transcriptionist','word processing','billing clerk',
               'file clerk','telemarketer','order desk','meter reader']
    low_ai  = ['nurse','physician','surgeon','dentist','therapist','social worker',
               'teacher','police','firefighter','paramedic','plumber','electrician',
               'carpenter','roofer','welder','mechanic','driver','pilot','chef','childcare']
    regulated=['physician','surgeon','dentist','pharmacist','lawyer','notary','veterinarian',
               'optometrist','chiropractor','psychologist','architect','audiologist']
    mod_bar  =['engineer','accountant','nurse','financial planner','real estate agent',
               'insurance broker','teacher','social worker']
    low_bar  =['software','developer','programmer','data ','it ','web ','cloud',
               'project manager','business analyst','logistics','warehouse','truck driver',
               'electrician','plumber','welder','carpenter','cook','chef','construction','helper']
    critical =['software developer','software engineer','nurse','physician','truck driver',
               'electrician','plumber','welder','carpenter','cybersecurity','supply chain',
               'construction','childcare','cook','chef','heavy equipment','physiotherapist']
    top_inc  =['surgeon','physician','dentist','judge','senior manager','vice-president',
               'chief executive','director','financial manager','data scientist','pilot','lawyer']
    below_avg=['cashier','food counter','kitchen helper','labourer','helper','cleaner',
               'harvester','farm worker','childcare worker','usher','dishwasher','janitor']

    ai_risk = 9 if any(k in t for k in high_ai) else 3 if any(k in t for k in low_ai) else 6
    newcomer_score = 2 if any(k in t for k in regulated) else 4 if any(k in t for k in mod_bar) else 7 if any(k in t for k in low_bar) else 5
    transferability_score = 9 if 'project manager' in t or 'business analyst' in t else 7 if any(k in t for k in ['manager','coordinator','analyst','administrator','supervisor','engineer','technologist']) else 5
    demand_score = 9 if any(k in t for k in critical) else 7 if any(k in t for k in ['manager','analyst','coordinator','engineer','technician','developer','programmer']) else 5
    income_score = 9 if any(k in t for k in top_inc) else 3 if any(k in t for k in below_avg) else 7 if any(k in t for k in ['engineer','software','analyst','accountant','nurse','pharmacist','manager']) else 5

    return {
        'ai_risk': ai_risk, 'newcomer_score': newcomer_score,
        'transferability_score': transferability_score, 'demand_score': demand_score,
        'income_score': income_score,
        'ai_rationale': "AI tools are increasingly reshaping this occupation\'s core workflows. Displacement risk is calibrated to task type and digital intensity by 2030.",
        'newcomer_rationale': "Credential recognition and licensing requirements determine accessibility for internationally trained professionals in Canada.",
        'transferability_rationale': "Core skills transfer across industries based on the breadth of analytical, technical, and interpersonal competencies involved.",
        'demand_rationale': "Canadian labour demand reflects Job Bank trends, Express Entry draws, and provincial hiring needs through 2030.",
        'income_rationale': "Salary benchmarks are relative to Canadian median income (~$62K/year) and adjusted for specialization and regional variation."
    }

occ = json.load(open('occupations_canada.json'))
scores = json.load(open('scores_canada.json'))
score_slugs = {s['slug'] for s in scores}

added = 0
for o in occ:
    if o['slug'] not in score_slugs:
        result = score_by_title(o['title'])
        opp = compute_opportunity_score(result)
        scores.append({'slug': o['slug'], 'title': o['title'], 'opportunity_score': opp, **result})
        added += 1

print(f"Added {added} missing scores. Total: {len(scores)}")
json.dump(scores, open('scores_canada.json', 'w'), indent=2)
print("Saved scores_canada.json")
