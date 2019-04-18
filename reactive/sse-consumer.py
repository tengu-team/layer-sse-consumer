#/usr/bin/env python3
from charms.reactive import (
    when,
    when_not,
    endpoint_from_flag,
)
from charms.reactive.flags import set_flag
from charmhelpers.core.hookenv import (
    log,
    status_set,
)

from charmhelpers.core import hookenv


from charms import layer


@when_not('layer.docker-resource.consumer_image.fetched')
def fetch_image():
    layer.docker_resource.fetch('consumer_image')


@when('consumer.configured')
def consumer_active():
    status_set('active', '')

@when_not('endpoint.sse-endpoint.joined')
def notify_relation_needed():
    status_set('blocked', 'Please add relationship to sse endpoint.')

@when('endpoint.sse-endpoint.joined')
@when_not('sse-endpoint.available')
def notify_waiting():
    status_set('waiting', 'Waiting for sse endpoint to send connection information.')

@when('layer.docker-resource.consumer_image.available')
@when('sse-endpoint.available')
@when_not('consumer.configured')
def config_consumer():
    status_set('maintenance', 'Configuring consumer container')
    endpoint = endpoint_from_flag('sse-endpoint.available')
    spec = make_pod_spec(endpoint.base_url)
    log('set pod spec:\n{}'.format(spec))
    layer.caas_base.pod_spec_set(spec)

    set_flag('consumer.configured')


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
