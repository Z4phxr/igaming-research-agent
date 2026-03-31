def test_list_prompts_returns_seeded_templates(client):
    response = client.get('/api/prompts')

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    keys = {item['key'] for item in body}
    assert 'analyzer.relevance_system' in keys
    assert 'analyzer.scoring_system' in keys
    assert 'analyzer.rejection_explain_system' in keys
    assert 'report_generator.briefing_system' in keys


def test_get_prompt_returns_detail_with_history(client):
    response = client.get('/api/prompts/analyzer.relevance_system')

    assert response.status_code == 200
    body = response.json()
    assert body['key'] == 'analyzer.relevance_system'
    assert isinstance(body['history'], list)
    assert len(body['history']) >= 1


def test_update_prompt_draft_and_publish(client):
    new_content = 'You are a strict binary filter. Return YES or NO only.'

    draft_response = client.put(
        '/api/prompts/analyzer.relevance_system/draft',
        json={'draft_content': new_content},
    )
    assert draft_response.status_code == 200
    assert draft_response.json()['draft_content'] == new_content

    publish_response = client.post(
        '/api/prompts/analyzer.relevance_system/publish',
        json={'content': new_content},
    )
    assert publish_response.status_code == 200
    body = publish_response.json()
    assert body['active_content'] == new_content
    assert body['draft_content'] == new_content
    assert body['active_version'] >= 2

    history_response = client.get('/api/prompts/analyzer.relevance_system/history')
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) >= 2
    assert history[0]['is_active'] is True
    assert history[0]['content'] == new_content
