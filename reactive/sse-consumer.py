#/usr/bin/env python3
from charms.reactive import (
    when,
    when_all,
    when_not,
    endpoint_from_flag,
    register_trigger,
)
from charms.reactive.flags import (
    set_flag,
    clear_flag,
)
from charmhelpers.core.hookenv import (
    log,
    status_set,
)

from charmhelpers.core import hookenv


from charms import layer


# https://discourse.jujucharms.com/t/trying-to-wrap-my-head-around-k8s-charms-pod-spec-set-creates-new-agent-and-removes-old-one/1384/4
#
# @when_not('endpoint.sse-endpoint.joined')
# def notify_relation_needed():
#     status_set('blocked', 'Please add relation to sse endpoint.')
#
#
# @when('endpoint.sse-endpoint.joined')
# @when_not('sse-endpoint.available')
# def notify_waiting():
#     status_set('waiting', 'Waiting for sse endpoint to send connection information.')


@when_all(
    'layer.docker-resource.consumer_image.available',
    'sse-endpoint.available')
@when_not('consumer.configured')
def config_consumer():
    status_set('maintenance', 'Configuring consumer container')
    endpoint = endpoint_from_flag('sse-endpoint.available')
    base_url = endpoint.base_url
    spec = make_pod_spec(base_url)
    log('set pod spec:\n{}'.format(spec))
    success = layer.caas_base.pod_spec_set(spec)

    if success:
        layer.status.maintenance('creating container')
        set_flag('consumer.configured')
        clear_flag('sse-endpoint.changed')
        status_set('active', 'Pods created ({})'.format(base_url))
    else:
        layer.status.blocked('k8s spec failed to deploy')


# If the sse-endpoint changes _while_ the consumer is configured,
# clear the flag so we reconfigure.
register_trigger(
    'sse-endpoint.changed',
    clear_flag='consumer.configured')


def make_pod_spec(base_url):
    with open('reactive/spec_template.yaml') as spec_file:
        pod_spec_template = spec_file.read()

    image_info = layer.docker_resource.get_info('consumer_image')

    data = {
        'name': hookenv.charm_name(),
        'docker_image_path': image_info.registry_path,
        'docker_image_username': image_info.username,
        'docker_image_password': image_info.password,
        'base_url': base_url,
    }
    return pod_spec_template.format(**data)
