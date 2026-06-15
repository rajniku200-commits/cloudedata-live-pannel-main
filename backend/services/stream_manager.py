

import base64
import os
from datetime import datetime


class StreamManager:
    def __init__(self):
        self.streams = {}
        self.viewers = {}
        self._recordings = {}

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
        frame = self._normalize_frame(frame)
        stream = self.streams.setdefault(agent_id, {'agent_id': agent_id})
        stream.update({
            'active': True,
            'agent_sid': sid,
            'last_frame': frame,
            'last_frame_at': datetime.utcnow(),
        })
        self._record_frame(agent_id, frame)
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

    def configure_stream(self, agent_id, settings):
        stream = self.streams.setdefault(agent_id, {'agent_id': agent_id})
        stream['settings'] = {
            'fps': int(settings.get('fps', 10)),
            'quality': int(settings.get('quality', 55)),
            'width': int(settings.get('width', 1280)),
            'height': int(settings.get('height', 720)),
        }
        return stream['settings']

    def start_recording(self, agent_id, recording_dir, user_id=None):
        os.makedirs(recording_dir, exist_ok=True)
        started = datetime.utcnow()
        folder = os.path.join(recording_dir, f'{agent_id}-{started.strftime("%Y%m%d%H%M%S")}')
        os.makedirs(folder, exist_ok=True)
        recording = {
            'agent_id': agent_id,
            'started_by': user_id,
            'started_at': started,
            'stopped_at': None,
            'folder': folder,
            'frame_count': 0,
            'last_saved_at': None,
        }
        self._recordings[agent_id] = recording
        return self._serialize_recording(recording)

    def stop_recording(self, agent_id):
        recording = self._recordings.get(agent_id)
        if not recording:
            return {'agent_id': agent_id, 'active': False}
        recording['stopped_at'] = datetime.utcnow()
        result = self._serialize_recording(recording)
        self._recordings.pop(agent_id, None)
        return result

    def recordings(self):
        return [self._serialize_recording(item) for item in self._recordings.values()]

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
            'recording': bool(self._recordings.get(agent_id)),
            'settings': stream.get('settings') or {},
        }

    def _normalize_frame(self, frame):
        if isinstance(frame, bytes):
            return 'data:image/jpeg;base64,' + base64.b64encode(frame).decode('ascii')
        if isinstance(frame, str) and not frame.startswith('data:image'):
            return 'data:image/jpeg;base64,' + frame
        return frame

    def _record_frame(self, agent_id, frame):
        recording = self._recordings.get(agent_id)
        if not recording or not isinstance(frame, str):
            return
        now = datetime.utcnow()
        last_saved = recording.get('last_saved_at')
        if last_saved and (now - last_saved).total_seconds() < 1:
            return
        try:
            payload = frame.split(',', 1)[1] if ',' in frame else frame
            content = base64.b64decode(payload)
            recording['frame_count'] += 1
            filename = f"frame-{recording['frame_count']:06d}.jpg"
            with open(os.path.join(recording['folder'], filename), 'wb') as handle:
                handle.write(content)
            recording['last_saved_at'] = now
        except Exception:
            return

    def _serialize_recording(self, recording):
        return {
            'agent_id': recording.get('agent_id'),
            'active': not bool(recording.get('stopped_at')),
            'started_by': recording.get('started_by'),
            'started_at': recording.get('started_at').isoformat() if recording.get('started_at') else None,
            'stopped_at': recording.get('stopped_at').isoformat() if recording.get('stopped_at') else None,
            'folder': recording.get('folder'),
            'frame_count': recording.get('frame_count', 0),
        }


stream_manager = StreamManager()


def save_frame(agent_id, sid, frame):
    return stream_manager.update_frame(agent_id, sid, frame)


def remove_sid(sid):
    removed = stream_manager.remove_agent_sid(sid)
    removed.extend(stream_manager.remove_viewer(sid))
    return sorted(set(removed))
