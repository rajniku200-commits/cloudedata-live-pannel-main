

from datetime import datetime


class StreamManager:
    def __init__(self):
        self.streams = {}
        self.viewers = {}

    def room_name(self, agent_id):
        return f'stream:{agent_id}'

    def start_stream(self, agent_id, started_by=None):
        stream = self.streams.setdefault(agent_id, {})
        stream.update({
            'agent_id': agent_id,
            'active': True,
            'started_by': started_by,
            'started_at': datetime.utcnow(),
            'stopped_at': None,
        })
        return stream

    def stop_stream(self, agent_id):
        stream = self.streams.setdefault(agent_id, {'agent_id': agent_id})
        stream.update({
            'active': False,
            'stopped_at': datetime.utcnow(),
        })
        self.viewers.pop(agent_id, None)
        return stream

    def update_frame(self, agent_id, sid, frame):
        stream = self.streams.setdefault(agent_id, {'agent_id': agent_id})
        stream.update({
            'active': True,
            'agent_sid': sid,
            'last_frame': frame,
            'last_frame_at': datetime.utcnow(),
        })
        return stream

    def get_frame(self, agent_id):
        stream = self.streams.get(agent_id) or {}
        return stream.get('last_frame')

    def add_viewer(self, agent_id, viewer_sid, user_id=None):
        viewers = self.viewers.setdefault(agent_id, {})
        viewers[viewer_sid] = {
            'sid': viewer_sid,
            'user_id': user_id,
            'joined_at': datetime.utcnow(),
        }
        return viewers[viewer_sid]

    def remove_viewer(self, viewer_sid):
        removed = []
        for agent_id, viewers in list(self.viewers.items()):
            if viewer_sid in viewers:
                del viewers[viewer_sid]
                removed.append(agent_id)
            if not viewers:
                del self.viewers[agent_id]
        return removed

    def remove_agent_sid(self, sid):
        removed = []
        for agent_id, stream in list(self.streams.items()):
            if stream.get('agent_sid') == sid:
                self.stop_stream(agent_id)
                removed.append(agent_id)
        return removed

    def status(self, agent_id=None):
        if agent_id:
            return self._serialize_stream(agent_id, self.streams.get(agent_id))
        return [self._serialize_stream(item_id, stream) for item_id, stream in self.streams.items()]

    def _serialize_stream(self, agent_id, stream):
        stream = stream or {'agent_id': agent_id, 'active': False}
        return {
            'agent_id': agent_id,
            'active': bool(stream.get('active')),
            'started_by': stream.get('started_by'),
            'started_at': stream.get('started_at').isoformat() if stream.get('started_at') else None,
            'stopped_at': stream.get('stopped_at').isoformat() if stream.get('stopped_at') else None,
            'last_frame_at': stream.get('last_frame_at').isoformat() if stream.get('last_frame_at') else None,
            'viewer_count': len(self.viewers.get(agent_id, {})),
        }


stream_manager = StreamManager()


def save_frame(agent_id, sid, frame):
    return stream_manager.update_frame(agent_id, sid, frame)


def remove_sid(sid):
    removed = stream_manager.remove_agent_sid(sid)
    removed.extend(stream_manager.remove_viewer(sid))
    return sorted(set(removed))
