from legal_assistant import respond
r=respond('My landlord will not return my security deposit of ₹15000 after I moved out.')
assert 'case_summary' in r and 'draft' in r and 'legal_citations' in r
assert 'No statute' in r['legal_citations']
r2=respond('My landlord is threatening to throw my belongings out tonight.')
assert 'safety' in r2
print('PASS: rental case is structured, unsupported citations are avoided, urgent threat is escalated.')
