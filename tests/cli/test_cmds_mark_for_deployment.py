# Copyright 2015-2016 Yelp Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os

import mock
from mock import ANY
from mock import patch
from pytest import raises

from paasta_tools.cli.cmds import mark_for_deployment
from paasta_tools.slack import PaastaSlackClient
from paasta_tools.utils import TimeoutError


class fake_args:
    deploy_group = 'test_deploy_group'
    service = 'test_service'
    git_url = 'git://false.repo/services/test_services'
    commit = 'd670460b4b4aece5915caf5c68d12f560a9fe3e4'
    soa_dir = 'fake_soa_dir'
    block = False
    verbose = False
    auto_rollback = False
    verify_image = False
    timeout = 10.0


@patch('paasta_tools.cli.cmds.mark_for_deployment.validate_service_name', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.mark_for_deployment', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.get_currently_deployed_sha', autospec=True)
def test_paasta_mark_for_deployment_acts_like_main(
    mock_get_currently_deployed_sha,
    mock_mark_for_deployment,
    mock_validate_service_name,
):
    mock_mark_for_deployment.return_value = 42
    assert mark_for_deployment.paasta_mark_for_deployment(fake_args) == 42
    mock_mark_for_deployment.assert_called_once_with(
        service='test_service',
        deploy_group='test_deploy_group',
        commit='d670460b4b4aece5915caf5c68d12f560a9fe3e4',
        git_url='git://false.repo/services/test_services',
    )
    assert mock_validate_service_name.called


@patch('paasta_tools.cli.cmds.mark_for_deployment._log', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment._log_audit', autospec=True)
@patch('paasta_tools.remote_git.create_remote_refs', autospec=True)
def test_mark_for_deployment_happy(mock_create_remote_refs, mock__log_audit, mock__log):
    actual = mark_for_deployment.mark_for_deployment(
        git_url='fake_git_url',
        deploy_group='fake_deploy_group',
        service='fake_service',
        commit='fake_commit',
    )
    assert actual == 0
    mock_create_remote_refs.assert_called_once_with(
        git_url='fake_git_url',
        ref_mutator=ANY,
        force=True,
    )
    mock__log_audit.assert_called_once_with(
        action='mark-for-deployment',
        action_details={'deploy_group': 'fake_deploy_group', 'commit': 'fake_commit'},
        service='fake_service',
    )


@patch('paasta_tools.cli.cmds.mark_for_deployment._log', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment._log_audit', autospec=True)
@patch('paasta_tools.remote_git.create_remote_refs', autospec=True)
def test_mark_for_deployment_sad(mock_create_remote_refs, mock__log_audit, mock__log):
    mock_create_remote_refs.side_effect = Exception('something bad')
    with patch('time.sleep', autospec=True):
        actual = mark_for_deployment.mark_for_deployment(
            git_url='fake_git_url',
            deploy_group='fake_deploy_group',
            service='fake_service',
            commit='fake_commit',
        )
    assert actual == 1
    assert mock_create_remote_refs.call_count == 3
    assert not mock__log_audit.called


@patch('paasta_tools.cli.cmds.mark_for_deployment.validate_service_name', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.mark_for_deployment', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.wait_for_deployment', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.get_currently_deployed_sha', autospec=True)
def test_paasta_mark_for_deployment_with_good_rollback(
    mock_get_currently_deployed_sha,
    mock_wait_for_deployment,
    mock_mark_for_deployment,
    mock_validate_service_name,
):
    class fake_args_rollback(fake_args):
        auto_rollback = True
        block = True
        timeout = 600

    mock_mark_for_deployment.return_value = 0
    mock_wait_for_deployment.side_effect = TimeoutError
    mock_get_currently_deployed_sha.return_value = "old-sha"
    with patch('time.sleep', autospec=True):
        assert mark_for_deployment.paasta_mark_for_deployment(fake_args_rollback) == 1
    mock_mark_for_deployment.assert_any_call(
        service='test_service',
        deploy_group='test_deploy_group',
        commit='d670460b4b4aece5915caf5c68d12f560a9fe3e4',
        git_url='git://false.repo/services/test_services',
    )
    mock_mark_for_deployment.assert_any_call(
        service='test_service',
        deploy_group='test_deploy_group',
        commit='old-sha',
        git_url='git://false.repo/services/test_services',
    )
    mock_mark_for_deployment.call_count = 2


@patch('paasta_tools.cli.cmds.mark_for_deployment.validate_service_name', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.is_docker_image_already_in_registry', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.get_currently_deployed_sha', autospec=True)
def test_paasta_mark_for_deployment_when_verify_image_fails(
    mock_get_currently_deployed_sha,
    mock_is_docker_image_already_in_registry,
    mock_validate_service_name,
):
    class fake_args_rollback(fake_args):
        verify_image = True

    mock_is_docker_image_already_in_registry.return_value = False
    with raises(ValueError):
        mark_for_deployment.paasta_mark_for_deployment(fake_args_rollback)


@patch('paasta_tools.cli.cmds.mark_for_deployment.validate_service_name', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.is_docker_image_already_in_registry', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.get_currently_deployed_sha', autospec=True)
def test_paasta_mark_for_deployment_when_verify_image_succeeds(
    mock_get_currently_deployed_sha,
    mock_is_docker_image_already_in_registry,
    mock_validate_service_name,
):
    class fake_args_rollback(fake_args):
        verify_image = True

    mock_is_docker_image_already_in_registry.return_value = True
    with patch('time.sleep', autospec=True):
        mark_for_deployment.paasta_mark_for_deployment(fake_args_rollback)
    mock_is_docker_image_already_in_registry.assert_called_with(
        'test_service',
        'fake_soa_dir',
        'd670460b4b4aece5915caf5c68d12f560a9fe3e4',
    )


@patch('paasta_tools.cli.cmds.mark_for_deployment.validate_service_name', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.mark_for_deployment', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.wait_for_deployment', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.get_currently_deployed_sha', autospec=True)
def test_paasta_mark_for_deployment_with_skips_rollback_when_same_sha(
    mock_get_currently_deployed_sha,
    mock_wait_for_deployment,
    mock_mark_for_deployment,
    mock_validate_service_name,
):
    class fake_args_rollback(fake_args):
        auto_rollback = True
        block = True
        timeout = 600

    mock_mark_for_deployment.return_value = 0
    mock_wait_for_deployment.side_effect = TimeoutError
    mock_get_currently_deployed_sha.return_value = "d670460b4b4aece5915caf5c68d12f560a9fe3e4"
    assert mark_for_deployment.paasta_mark_for_deployment(fake_args_rollback) == 1
    mock_mark_for_deployment.assert_called_once_with(
        service='test_service',
        deploy_group='test_deploy_group',
        commit='d670460b4b4aece5915caf5c68d12f560a9fe3e4',
        git_url='git://false.repo/services/test_services',
    )


@patch('paasta_tools.cli.cmds.mark_for_deployment.get_slack_client', autospec=True)
@patch('paasta_tools.remote_git.get_authors', autospec=True)
def test_slack_deploy_notifier(mock_get_authors, mock_client):
    fake_psc = mock.create_autospec(PaastaSlackClient)
    fake_psc.post.return_value = [{'ok': True, 'message': {'ts': 1234}}]
    mock_client.return_value = fake_psc
    mock_get_authors.return_value = 0, "fakeuser1 fakeuser2"
    sdn = mark_for_deployment.SlackDeployNotifier(
        service='testservice',
        deploy_info={
            'pipeline':
            [
                {'step': 'test_deploy_group', 'slack_notify': True, },
            ],
            'slack_channels': ['#webcore', '#webcore2'],
        },
        deploy_group='test_deploy_group',
        commit='newcommit',
        old_commit='oldcommit',
        git_url="foo",
    )
    assert sdn.notify_after_mark(ret=1) is None
    assert sdn.notify_after_mark(ret=0) is None
    assert sdn.notify_after_good_deploy() is None
    assert sdn.notify_after_auto_rollback() is None
    assert sdn.notify_after_abort() is None
    assert fake_psc.post.call_count > 0, fake_psc.post.call_args
    assert sdn.get_authors_to_be_notified() == "Authors: <@fakeuser1>, <@fakeuser2>"

    with mock.patch.dict(
        os.environ,
        {'BUILD_URL': 'https://www.yelp.com'},
        clear=True,
    ):
        assert sdn.get_url_message() == '<https://www.yelp.com/consoleFull|Jenkins Job>'


@patch('paasta_tools.cli.cmds.mark_for_deployment.get_slack_client', autospec=True)
@patch('paasta_tools.remote_git.get_authors', autospec=True)
def test_slack_deploy_notifier_with_auto_rollbacks(mock_get_authors, mock_client):
    fake_psc = mock.create_autospec(PaastaSlackClient)
    fake_psc.post.return_value = [{'ok': True, 'message': {'ts': 1234}}]
    mock_client.return_value = fake_psc
    mock_get_authors.return_value = 0, "fakeuser1 fakeuser2"
    sdn = mark_for_deployment.SlackDeployNotifier(
        service='testservice',
        deploy_info={
            'pipeline':
            [
                {'step': 'test_deploy_group', 'slack_notify': True, },
            ],
            'slack_channels': ['#webcore', '#webcore2'],
        },
        deploy_group='test_deploy_group',
        commit='newcommit',
        old_commit='oldcommit',
        git_url="foo",
        auto_rollback=True,
    )
    assert sdn.notify_after_mark(ret=1) is None
    assert sdn.notify_after_mark(ret=0) is None
    assert sdn.notify_after_good_deploy() is None
    assert sdn.notify_after_auto_rollback() is None
    assert sdn.notify_after_abort() is None
    assert fake_psc.post.call_count > 0, fake_psc.post.call_args
    assert sdn.get_authors_to_be_notified() == "Authors: <@fakeuser1>, <@fakeuser2>"


@patch('paasta_tools.cli.cmds.mark_for_deployment.get_slack_client', autospec=True)
@patch('paasta_tools.remote_git.get_authors', autospec=True)
def test_slack_deploy_notifier_on_non_notify_groups(mock_get_authors, mock_client):
    fake_psc = mock.create_autospec(PaastaSlackClient)
    mock_client.return_value = fake_psc
    mock_get_authors.return_value = 1, "fakeuser1 fakeuser2"
    sdn = mark_for_deployment.SlackDeployNotifier(
        service='testservice',
        deploy_info={
            'pipeline':
            [
                {'step': 'test_deploy_group', 'slack_notify': False, },
            ],
        },
        deploy_group='test_deploy_group',
        commit='newcommit',
        old_commit='oldcommit',
        git_url="foo",
    )
    assert sdn.notify_after_mark(ret=1) is None
    assert sdn.notify_after_mark(ret=0) is None
    assert sdn.notify_after_good_deploy() is None
    assert sdn.notify_after_auto_rollback() is None
    assert sdn.notify_after_abort() is None
    assert fake_psc.post.call_count == 0, fake_psc.post.call_args


@patch('paasta_tools.cli.cmds.mark_for_deployment.get_slack_client', autospec=True)
@patch('paasta_tools.remote_git.get_authors', autospec=True)
def test_slack_deploy_notifier_doesnt_notify_on_same_commit(mock_get_authors, mock_client):
    fake_psc = mock.create_autospec(PaastaSlackClient)
    mock_client.return_value = fake_psc
    mock_get_authors.return_value = 0, "fakeuser1 fakeuser2"
    sdn = mark_for_deployment.SlackDeployNotifier(
        service='testservice',
        deploy_info={
            'pipeline':
            [
                {'step': 'test_deploy_group', 'slack_notify': True, },
            ],
            'slack_channels': ['#webcore', '#webcore2'],
        },
        deploy_group='test_deploy_group',
        commit='samecommit',
        old_commit='samecommit',
        git_url="foo",
    )
    assert sdn.notify_after_mark(ret=1) is None
    assert sdn.notify_after_mark(ret=0) is None
    assert sdn.notify_after_good_deploy() is None
    assert sdn.notify_after_auto_rollback() is None
    assert sdn.notify_after_abort() is None
    assert fake_psc.post.call_count == 0, fake_psc.post.call_args
    assert sdn.get_authors_to_be_notified() == "Authors: <@fakeuser1>, <@fakeuser2>"


@patch('paasta_tools.cli.cmds.mark_for_deployment.get_slack_client', autospec=True)
@patch('paasta_tools.remote_git.get_authors', autospec=True)
def test_slack_deploy_notifier_notifies_on_deploy_info_flags(mock_get_authors, mock_client):
    fake_psc = mock.create_autospec(PaastaSlackClient)
    fake_psc.post.return_value = [{'ok': True, 'message': {'ts': 1234}}]
    mock_client.return_value = fake_psc
    mock_get_authors.return_value = 0, "fakeuser1 fakeuser2"
    sdn = mark_for_deployment.SlackDeployNotifier(
        service='testservice',
        deploy_info={
            'pipeline': [
                {
                    'step': 'test_deploy_group',
                    'notify_after_mark': True,
                    'notify_after_good_deploy': True,
                    'notify_after_auto_rollback': True,
                    'notify_after_abort': True,
                },
            ],
            'slack_channels': ['#webcore', '#webcore2'],
        },
        deploy_group='test_deploy_group',
        commit='newcommit',
        old_commit='oldcommit',
        git_url="foo",
    )
    assert sdn.notify_after_mark(ret=1) is None
    assert sdn.notify_after_mark(ret=0) is None
    assert sdn.notify_after_good_deploy() is None
    assert sdn.notify_after_auto_rollback() is None
    assert sdn.notify_after_abort() is None
    assert fake_psc.post.call_count > 0, fake_psc.post.call_args
    assert sdn.get_authors_to_be_notified() == "Authors: <@fakeuser1>, <@fakeuser2>"
    assert "Jenkins" or "Run by" in sdn.get_url_message()


@patch('paasta_tools.cli.cmds.mark_for_deployment.get_slack_client', autospec=True)
@patch('paasta_tools.remote_git.get_authors', autospec=True)
def test_slack_deploy_notifier_doesnt_notify_on_deploy_info_flags(mock_get_authors, mock_client):
    fake_psc = mock.create_autospec(PaastaSlackClient)
    mock_client.return_value = fake_psc
    mock_get_authors.return_value = 0, "fakeuser1 fakeuser2"
    sdn = mark_for_deployment.SlackDeployNotifier(
        service='testservice',
        deploy_info={
            'pipeline':
            [
                {
                    'step': 'test_deploy_group',
                    'slack_notify': True,
                    'notify_after_mark': False,
                    'notify_after_good_deploy': False,
                    'notify_after_auto_rollback': False,
                    'notify_after_abort': False,
                },
            ],
        },
        deploy_group='test_deploy_group',
        commit='newcommit',
        old_commit='oldcommit',
        git_url="foo",
    )
    assert sdn.notify_after_mark(ret=1) is None
    assert sdn.notify_after_mark(ret=0) is None
    assert sdn.notify_after_good_deploy() is None
    assert sdn.notify_after_auto_rollback() is None
    assert sdn.notify_after_abort() is None
    assert fake_psc.post.call_count == 0, fake_psc.post.call_args
    assert sdn.get_authors_to_be_notified() == "Authors: <@fakeuser1>, <@fakeuser2>"


@patch('paasta_tools.cli.cmds.mark_for_deployment.SlackDeployNotifier', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.mark_for_deployment', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.wait_for_deployment', autospec=True)
def test_MarkForDeployProcess_handles_wait_for_deployment_failure(
    mock_wait_for_deployment,
    mock_mark_for_deployment,
    mock_SlackDeployNotifier,
):
    mfdp = mark_for_deployment.MarkForDeploymentProcess(
        service='service',
        block=True,
        auto_rollback=True,

        deploy_info=None,
        deploy_group=None,
        commit='abc1234578912',
        old_git_sha=None,
        git_url=None,
        soa_dir=None,
        timeout=None,
    )

    mock_mark_for_deployment.return_value = 0
    mock_wait_for_deployment.side_effect = Exception()

    retval = mfdp.run()

    assert mock_mark_for_deployment.call_count == 1
    assert mock_wait_for_deployment.call_count == 1
    assert retval == 1
    assert mfdp.state == 'deploy_aborted'


@patch('paasta_tools.cli.cmds.mark_for_deployment.SlackDeployNotifier', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.mark_for_deployment', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.wait_for_deployment', autospec=True)
@patch('time.sleep', autospec=True)
def test_MarkForDeployProcess_handles_wait_for_deployment_cancelled(
    mock_sleep,
    mock_wait_for_deployment,
    mock_mark_for_deployment,
    mock_SlackDeployNotifier,
):
    mfdp = mark_for_deployment.MarkForDeploymentProcess(
        service='service',
        block=True,
        # For this test, auto_rollback must be True so that the deploy_cancelled trigger takes us to start_rollback
        # instead of deploy_aborted.
        auto_rollback=True,

        deploy_info=None,
        deploy_group=None,
        commit='abc123853489',
        old_git_sha=None,
        git_url=None,
        soa_dir=None,
        timeout=None,
    )

    mock_mark_for_deployment.return_value = 0
    mock_wait_for_deployment.side_effect = KeyboardInterrupt()

    retval = mfdp.run()

    # This should happen once for the initial deploy, then once for the rollback.
    assert mock_mark_for_deployment.call_count == 2
    # TODO: we should wait for the rollback to finish
    assert mock_wait_for_deployment.call_count == 1
    assert retval == 1
    assert mfdp.state == 'start_rollback'


@patch('paasta_tools.cli.cmds.mark_for_deployment.SlackDeployNotifier', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.mark_for_deployment', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.wait_for_deployment', autospec=True)
def test_MarkForDeployProcess_skips_wait_for_deployment_when_block_is_False(
    mock_wait_for_deployment,
    mock_mark_for_deployment,
    mock_SlackDeployNotifier,
):
    mfdp = mark_for_deployment.MarkForDeploymentProcess(
        service='service',
        block=False,
        auto_rollback=False,

        deploy_info=None,
        deploy_group=None,
        commit='abc123456789',
        old_git_sha=None,
        git_url=None,
        soa_dir=None,
        timeout=None,
    )

    mock_mark_for_deployment.return_value = 0
    mock_wait_for_deployment.side_effect = Exception()

    retval = mfdp.run()

    assert mock_mark_for_deployment.call_count == 1
    assert mock_wait_for_deployment.call_count == 0
    assert retval == 0
    assert mfdp.state == 'deploying'


@patch('time.sleep', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.mark_for_deployment', autospec=True)
@patch('paasta_tools.cli.cmds.mark_for_deployment.wait_for_deployment', autospec=True)
def test_MarkForDeployProcess_goes_to_mfd_failed_when_mark_for_deployment_fails(
    mock_wait_for_deployment,
    mock_mark_for_deployment,
    mock_sleep,
):
    mfdp = mark_for_deployment.MarkForDeploymentProcess(
        service='service',
        block=False,  # shouldn't matter for this test
        auto_rollback=False,  # shouldn't matter for this test

        deploy_info=None,
        deploy_group=None,
        commit='abc123456789',
        old_git_sha=None,
        git_url=None,
        soa_dir=None,
        timeout=None,
    )

    mock_mark_for_deployment.return_value = 1
    mock_wait_for_deployment.side_effect = Exception()

    retval = mfdp.run()

    assert mock_mark_for_deployment.call_count == 1
    assert mock_wait_for_deployment.call_count == 0
    assert retval == 1
    assert mfdp.state == 'mfd_failed'
