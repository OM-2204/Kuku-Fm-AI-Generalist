from llm_ranker import hybrid_score, estimate_cost, _extract_json, SCHEMA

class FakeUsage:
    input_tokens = 100
    output_tokens = 50
class FakeResponse:
    output_text = '{"hook_score":8,"emotional_intensity":7,"conflict_tension":9,"cliffhanger_score":8,"standalone_clarity":7,"llm_score":78,"hook_explanation":"Immediate threat.","cliffhanger_explanation":"Unresolved threat.","why_it_works":"Clear conflict and suspense.","weaknesses":[],"recommendation":"HIGH"}'
    usage = FakeUsage()

def test_hybrid():
    assert hybrid_score(90, 70) == 78.0

def test_cost_estimate_is_positive():
    assert estimate_cost(4000) > 0

def test_structured_json_validation():
    result = _extract_json(FakeResponse())
    assert result['llm_score'] == 78
    assert result['recommendation'] == 'HIGH'

if __name__ == '__main__':
    test_hybrid(); test_cost_estimate_is_positive(); test_structured_json_validation()
    print('PASS: hybrid scoring, cost estimate and structured JSON validation.')
