"""Narrow-scope Indian rental-deposit helper. No fabricated statutes/case law."""
import re

DISCLAIMER = ('This is a general information and drafting aid, not a lawyer or a substitute for legal advice. '
              'The result depends on your agreement, state/city, evidence and facts. Do not treat this as a legal opinion.')

def extract_amount(text):
    m=re.search(r'(?:₹|rs\.?\s*)\s?([\d,]+)',text,re.I)
    return '₹'+m.group(1) if m else '[amount]'

def build_case(text, name='[Your name]', landlord='[Landlord name]', address='[Rental property address]', city='[City, State]'):
    t=text.lower(); amount=extract_amount(text)
    dates=re.findall(r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4})\b',text,re.I)
    issues=[]
    if any(x in t for x in ['deposit','security','advance','refund']):issues.append('Return of rental security deposit / advance')
    if any(x in t for x in ['deduct','damage','repair','painting','cleaning']):issues.append('Possible deductions or damage dispute')
    if any(x in t for x in ['vacat','left the flat','handed over','keys']):issues.append('Possession handover / move-out')
    if any(x in t for x in ['agreement','rent deed','lease']):issues.append('Rental agreement terms need review')
    missing=[]
    for label,terms in [('Signed rent agreement',['agreement','rent deed','lease']),('Payment proof',['upi','bank','receipt','paid','transfer']),('Move-out / key handover proof',['handed over','keys','vacat','left the flat']),('Written refund request and landlord response',['whatsapp','message','email','asked','refused'])]:
        if not any(w in t for w in terms):missing.append(label)
    questions=[]
    # Ask only for facts that do not appear to be present in the user's account.
    if not re.search(r'\b(?:in|at)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?', text):
        questions.append('Which city and state is the rental property in?')
    if amount == '[amount]':
        questions.append('What was the deposit amount, and how was it paid?')
    if not dates:
        questions.append('What were the move-in and move-out / key-handover dates?')
    if not any(x in t for x in ['painting','cleaning','damage','deduct','withhold','refus','not returned']):
        questions.append('What reason has the landlord given for withholding the deposit?')
    if not any(x in t for x in ['agreement','rent deed','lease']):
        questions.append('What does the written agreement say about refund timing and deductions?')
    return {'issue':issues or ['Possible rental deposit / tenancy dispute; confirm exact issue'], 'amount_mentioned':amount,
            'dates_mentioned':dates, 'facts_as_provided':text.strip(), 'evidence_to_collect':[
            'Rent / leave-and-license agreement and clauses on deposit, notice and deductions',
            'Bank statement, UPI transaction ID or receipt showing deposit payment',
            'Move-in and move-out photos/videos; inventory and meter readings',
            'Proof of notice and key / possession handover',
            'WhatsApp, SMS and email exchanges about refund and deductions'],
            'missing_or_unconfirmed':missing, 'questions_to_resolve':questions}

def draft_notice(text, tenant='[Tenant name]', landlord='[Landlord name]', property_address='[Property address]', city='[City, State]', amount=None):
    amount=amount or extract_amount(text)
    return f'''DRAFT — FOR REVIEW\n\nDate: [DD/MM/YYYY]\nTo,\n{landlord}\n[Landlord address]\n\nSubject: Request for refund / itemised account of rental security deposit\n\nDear {landlord},\n\nI, {tenant}, was the tenant of {property_address}. I paid a security deposit of {amount} in connection with the tenancy. I vacated / handed over possession on [date] and returned the keys on [date] (please correct these details to match the evidence).\n\nI request you to refund the outstanding security deposit of {amount} within 7 days of receiving this letter (a proposed response period, not a statutory deadline), or provide within the same period an itemised statement of any proposed deductions, with supporting bills, photographs and the relevant clause of our rental agreement. If any amount has already been refunded or lawfully adjusted, please share the calculation and payment details.\n\nPlease communicate in writing to [email / phone]. I hope this can be resolved amicably. If it is not resolved, I may consider appropriate remedies available under the agreement and applicable law after obtaining local legal advice.\n\nRegards,\n{tenant}\n[Address]\n[Phone / Email]\n\nFacts supplied by the user (for verification):\n{text}\n\nBefore sending: verify every date and amount, attach only genuine evidence, check the agreement and local law, and consider review by an advocate. This template is not a formal legal notice.'''

def respond(text):
    t=text.lower()
    if any(k in t for k in ['police','arrest','violence','threat','evict tonight','lockout','domestic abuse','suicide','self harm']):
        return {'safety':'This may involve immediate safety or urgent legal risk. Contact local emergency services / police if in immediate danger and speak to a qualified local lawyer or legal aid service promptly. Do not rely on this tool for urgent action.', 'disclaimer':DISCLAIMER}
    if not any(k in t for k in ['deposit','security','landlord','tenant','rent','flat','house','refund']):
        return {'message':'This prototype currently handles one narrow area: rental security-deposit refunds in India. Please describe the rental, deposit, move-out and refund dispute.', 'disclaimer':DISCLAIMER}
    case=build_case(text)
    return {'plain_language':'From what you described, the issue appears to be a possible dispute about return of a rental security deposit. The exact position depends on the signed agreement, proof of payment, handover date, deductions and the state/city. A landlord may claim deductions, but ask for the contractual basis and an itemised explanation rather than assuming every deduction is valid.',
            'case_summary':case,'next_steps':['Keep the original agreement and payment proof safe.','Send a calm written request asking for the refund or itemised deductions.','Keep proof that the message was delivered and save the reply.','If unresolved, consult a local advocate or District Legal Services Authority about appropriate options.'],
            'draft':draft_notice(text), 'legal_citations':'No statute, section or court case is cited by this prototype. It deliberately avoids unverified legal references.', 'disclaimer':DISCLAIMER}
