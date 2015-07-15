import eventlet
import httplib2
from pprint import pprint

from st2reactor.sensor.base import PollingSensor

try:
    from simplejson import loads, dumps
except ImportError:
    from json import loads, dumps

class ZabbixSensor(PollingSensor):
    def __init__(self, sensor_service, config):
        super(ZabbixSensor, self).__init__(sensor_service=sensor_service, config=config)
        self._logger = self._sensor_service.get_logger(name=self.__class__.__name__)
        self._stop = False
        self._logger.debug('ZabbixSensor init...')

    def setup(self):
        self._logger.debug('ZabbixSensor setup...')
        pass

    def poll(self):
        self.set_poll_interval(600)
        self._logger.debug('ZabbixSensor dispatching trigger...')
        if not self._config['zabbix_triggers_poll_enabled']:
            self._logger.debug('ZabbixSensor DISABLED')
            return
        for server in self._config.get('zabbix_servers',[]):
            self.poll_server(server)
   
    def poll_server(self,server):
        zabbix = httplib2.Http()
        auth = {"jsonrpc": "2.0","method": "user.login","params": {"user": server["user"],"password": server["passwd"]},"id": 1,"auth": None}
        resp, auth_content = zabbix.request(
            uri=server["url"],
            method='POST',
            headers={'Content-Type': 'application/json; charset=UTF-8'},
            body=dumps(auth),
        )
#        pprint(auth_content)
        auth_json = loads(auth_content)
#        print auth_json["result"]
        auth_tocken = auth_json["result"]
        triggers = {
            "jsonrpc": "2.0",
            "method": "trigger.get",
            "params": {
                "output": [
                "triggerid",
                "description",
                "comments",
                "priority"
                ],
                "filter": {
                    "value": 1
                },
                "selectHosts": ["name"],
                "only_true": "1",
                "active": "1",
                "monitored": "1",
                "withUnacknowledgedEvents":"1",
                "min_severity": self._config['zabbix_min_severity'],
                "sortfield": "priority",
                "sortorder": "DESC"
            },
            "auth": auth_tocken,
            "id": 2
        }

        resp, triggers_content = zabbix.request(
            uri=server["url"],
            method='POST',
            headers={'Content-Type': 'application/json; charset=UTF-8'},
            body=dumps(triggers),
        )
#        pprint(triggers_content)
        all_triggers = loads(triggers_content)["result"]
        for trigger in all_triggers:
            payload = {
                'host': trigger["hosts"][0]["name"],
                'triggerid': trigger["triggerid"],
                'description': trigger["description"],
                'priority': trigger["priority"],
                'url': server['url'],
                'comment': server['comment'],
            }
            self._sensor_service.dispatch(trigger='st2-chatops-misc.event2', payload=payload)

    def cleanup(self):
        self._stop = True

    # Methods required for programmable sensors.
    def add_trigger(self, trigger):
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass
