from paasta_tools import automatic_rollbacks

REAL_ROLLBACK_PRESS = {'type': 'block_actions', 'team': {'id': 'T0289TLJY', 'domain': 'yelp'}, 'user': {'id': 'UA6JBNA0Z', 'username': 'kwa', 'team_id': 'T0289TLJY'}, 'api_app_id': 'AAJ7PL9ST', 'token': 'WYj864vvUYGtcV4pyfmO4rOQ', 'container': {'type': 'message', 'message_ts': '1551306063.241500', 'channel_id': 'CA05GTDB9', 'is_ephemeral': False, 'thread_ts': '1551306063.241500'}, 'trigger_id': '562162233904.2281938644.c15af7fa5b7e10836c6db7ece2f53eab', 'channel': {'id': 'CA05GTDB9', 'name': 'paasta'}, 'message': {'type': 'message', 'subtype': 'bot_message', 'text': "This content can't be displayed.", 'ts': '1551306063.241500', 'username': 'PaaSTA', 'bot_id': 'BAJ8JMV9V', 'thread_ts': '1551306063.241500', 'reply_count': 1, 'reply_users_count': 1, 'latest_reply': '1551306064.241600', 'reply_users': ['BAJ8JMV9V'], 'replies': [{'user': 'BAJ8JMV9V', 'ts': '1551306064.241600'}], 'subscribed': False, 'blocks': [{'type': 'section', 'block_id': 'K15S', 'text': {'type': 'mrkdwn', 'text': '*compute-infra-test-service* - Marked *baaf4d7b2ddf* for deployment on *mesosstage.everything*.\n', 'verbatim': False}}, {'type': 'actions', 'block_id': 'rollback_block1', 'elements': [{'type': 'button', 'action_id': 'cLjFK', 'text': {'type': 'plain_text', 'text': 'Roll Back (Not Implemented)', 'emoji': True}, 'value': 'rollback'}, {'type': 'button', 'action_id': 'Grjq', 'text': {'type': 'plain_text', 'text': 'Continue (Not Implemented)', 'emoji': True}, 'value': 'continue'}]}]}, 'response_url': 'https://hooks.slack.com/actions/T0289TLJY/562866820372/0lRlD5JFQlLPPvqrelCpJlF9', 'actions': [{'action_id': 'cLjFK', 'block_id': 'rollback_block1', 'text': {'type': 'plain_text', 'text': 'Roll Back (Not Implemented)', 'emoji': True}, 'value': 'rollback', 'type': 'button', 'action_ts': '1551306127.199355'}]}  # noqa E501


def test_get_slack_blocks_for_deployment_happy_path():
    blocks = automatic_rollbacks.get_slack_blocks_for_deployment("test")
    assert blocks[0]["text"]["text"] == "test"


def test_event_to_buttonpress_rollback():
    actual = automatic_rollbacks.event_to_buttonpress(REAL_ROLLBACK_PRESS)
    assert actual.username == 'kwa'
    assert actual.action == 'rollback'
