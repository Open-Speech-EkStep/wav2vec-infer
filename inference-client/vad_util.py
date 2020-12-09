import collections

import webrtcvad


class Frame(object):
    """Represents a "frame" of audio data."""

    def __init__(self, bytes, timestamp, duration):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration


def frame_generator(frame_duration_ms, audio, sample_rate):
    n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
    offset = 0
    timestamp = 0.0
    duration = (float(n) / sample_rate) / 2.0
    while offset + n < len(audio):
        yield Frame(audio[offset:offset + n], timestamp, duration)
        timestamp += duration
        offset += n


def vad_collector(sample_rate, frame_duration_ms,
                  padding_duration_ms, vad, frames):
    num_padding_frames = int(padding_duration_ms / frame_duration_ms)
    # We use a deque for our sliding window/ring buffer.
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    # We have two states: TRIGGERED and NOTTRIGGERED. We start in the
    # NOTTRIGGERED state.
    triggered = False

    voiced_frames = []

    # silence, byte cut

    for frame in frames:
        is_speech = vad.is_speech(frame.bytes, sample_rate)
        print(frame, is_speech)
        # if not triggered:
        #     ring_buffer.append((frame, is_speech))
        #     num_voiced = len([f for f, speech in ring_buffer if speech])
        #     # If we're NOTTRIGGERED and more than 90% of the frames in
        #     # the ring buffer are voiced frames, then enter the
        #     # TRIGGERED state.
        #     if num_voiced > 0.5 * ring_buffer.maxlen:
        #         triggered = True
        #         # We want to yield all the audio we see from now until
        #         # we are NOTTRIGGERED, but we have to start with the
        #         # audio that's already in the ring buffer.
        #         for f, s in ring_buffer:
        #             voiced_frames.append(f)
        #         ring_buffer.clear()
        # else:
        #     # We're in the TRIGGERED state, so collect the audio data
        #     # and add it to the ring buffer.
        #     voiced_frames.append(frame)
        #     ring_buffer.append((frame, is_speech))
        #     num_unvoiced = len([f for f, speech in ring_buffer if not speech])
        #     # If more than 90% of the frames in the ring buffer are
        #     # unvoiced, then enter NOTTRIGGERED and yield whatever
        #     # audio we've collected.
        #     if num_unvoiced > 0.9 * ring_buffer.maxlen:
        #         triggered = False
        #         yield b''.join([f.bytes for f in voiced_frames])
        #         ring_buffer.clear()
        #         voiced_frames = []
    # If we have any leftover voiced audio when we run out of input,
    # yield it.
    # if voiced_frames:
    #     yield b''.join([f.bytes for f in voiced_frames])


# def process_audio_by_vad(chunk):
#     sample_rate = 16000
#     vad = webrtcvad.Vad(3)
#     frames = frame_generator(30, chunk, sample_rate)
#     segments = vad_collector(sample_rate, 30, 300, vad, list(frames))
#     audio = []
#     for segment in segments:
#         audio.append(segment)
#     return audio


if __name__ == '__main__':
    count = 1
    while count < 15:
        print("working on " + str(count))
        with open('603c62545ba14a87acb6def435f2780c_{}.wav'.format(count), 'rb') as f:
            chunk = f.read()
        count += 1
        sample_rate = 16000
        vad = webrtcvad.Vad(3)
        frames = frame_generator(30, chunk, sample_rate)
        vad_collector(sample_rate, 30, 300, vad, list(frames))
