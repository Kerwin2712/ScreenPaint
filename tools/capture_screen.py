import cv2
import numpy as np
import datetime
import time
import os
import tempfile
import threading
import subprocess
import queue
from PyQt6.QtCore import QThread, pyqtSignal

def take_screenshot(rect=None, filename=None):
    """Captura rápida de pantalla."""
    import mss
    if not filename:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{ts}.png"

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        if rect:
            monitor = {"top": rect.y(), "left": rect.x(), "width": rect.width(), "height": rect.height()}
        img = sct.grab(monitor)
        frame = np.frombuffer(img.raw, dtype=np.uint8).reshape((img.height, img.width, 4))
        cv2.imwrite(filename, cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR))
    return filename

import pyaudio
import wave

def _get_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except:
        return "ffmpeg"

class AudioRecorder(threading.Thread):
    def __init__(self, filename, rate=44100, channels=2, chunk=1024):
        super().__init__(daemon=True)
        self.filename = filename
        self.rate = rate
        self.channels = channels
        self.chunk = chunk
        self._stop_event = threading.Event()
        self._paused = False
        self.start_time = None

    def run(self):
        p = pyaudio.PyAudio()
        try:
            stream = p.open(format=pyaudio.paInt16, channels=self.channels, rate=self.rate, input=True, frames_per_buffer=self.chunk)
            frames = []
            self.start_time = time.perf_counter()
            while not self._stop_event.is_set():
                if self._paused:
                    time.sleep(0.01)
                    continue
                try:
                    data = stream.read(self.chunk, exception_on_overflow=False)
                    frames.append(data)
                except:
                    continue
            stream.stop_stream()
            stream.close()
            wf = wave.open(self.filename, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(frames))
            wf.close()
        except Exception as e:
            print(f"Audio Error: {e}")
        finally:
            p.terminate()

    def pause(self): self._paused = not self._paused
    def stop(self):
        self._stop_event.set()
        self.join(timeout=1)

class ScreenRecorder(QThread):
    """
    Motor de grabación avanzado:
    Usa una cola de frames para desacoplar mss (captura) de ffmpeg (codificación).
    """
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    error_occurred = pyqtSignal(str)
    processing_started = pyqtSignal()
    progress_updated = pyqtSignal(int)

    _TARGET_FPS = 12.0 # Ajustado para balancear calidad y rendimiento en equipos variados

    def __init__(self, rect=None, geometry_source=None, output_filename=None, audio_enabled=True):
        super().__init__()
        self.rect = rect
        self.geometry_source = geometry_source
        self.output_filename = output_filename
        self.audio_enabled = audio_enabled
        self.is_recording = False
        self.is_paused = False
        self._audio_rec = None
        self._video_start = None
        self._frame_queue = queue.Queue(maxsize=30)
        self._video_duration = 0

    def run(self):
        import mss
        with mss.mss() as sct:
            if self.rect:
                g = self.rect
                monitor = {"top": g.y(), "left": g.x(), "width": g.width(), "height": g.height()}
            elif self.geometry_source:
                g = self.geometry_source()
                monitor = {"top": g.y(), "left": g.x(), "width": g.width(), "height": g.height()}
            else:
                monitor = sct.monitors[1]
            w, h = monitor["width"], monitor["height"]

        tmp_dir = tempfile.gettempdir()
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        vid_tmp = os.path.join(tmp_dir, f"sp_raw_{ts}.mp4")
        aud_tmp = os.path.join(tmp_dir, f"sp_aud_{ts}.wav")

        if self.audio_enabled:
            self._audio_rec = AudioRecorder(aud_tmp)
            self._audio_rec.start()
            while self._audio_rec.start_time is None: time.sleep(0.001)

        ffmpeg_exe = _get_ffmpeg()
        command = [
            ffmpeg_exe, '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo', '-s', f'{w}x{h}',
            '-pix_fmt', 'bgra', '-r', str(self._TARGET_FPS), '-i', '-',
            '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', '-crf', '28', vid_tmp
        ]

        # DEVNULL en stderr es vital para evitar bloqueos por buffer lleno
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        self.is_recording = True
        self.recording_started.emit()
        self._video_start = time.perf_counter()
        
        # Hilo de codificación/escritura
        def encoder():
            while self.is_recording or not self._frame_queue.empty():
                try:
                    frame = self._frame_queue.get(timeout=0.1)
                    if frame is not None:
                        proc.stdin.write(frame)
                    self._frame_queue.task_done()
                except queue.Empty: continue
                except Exception as e:
                    print(f"Encoder error: {e}")
                    break
            if proc.stdin: proc.stdin.close()
            proc.wait()

        encode_thread = threading.Thread(target=encoder, daemon=True)
        encode_thread.start()

        frame_dur = 1.0 / self._TARGET_FPS
        try:
            with mss.mss() as sct:
                while self.is_recording:
                    if self.is_paused:
                        time.sleep(0.05)
                        continue
                    
                    t_start = time.perf_counter()
                    img = sct.grab(monitor)
                    
                    try: self._frame_queue.put(img.raw, block=False)
                    except queue.Full: pass # Drop frame if too slow
                    
                    elapsed = time.perf_counter() - t_start
                    wait = frame_dur - elapsed
                    if wait > 0: time.sleep(wait)
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.is_recording = False
            encode_thread.join(timeout=3)
            self._video_duration = time.perf_counter() - self._video_start

        if self._audio_rec: self._audio_rec.stop()

        final_out = self.output_filename or os.path.join(tmp_dir, f"final_{ts}.mp4")
        try:
            self.processing_started.emit()
            if self.audio_enabled and os.path.exists(aud_tmp):
                offset = max(0, self._video_start - self._audio_rec.start_time)
                self._merge_final(vid_tmp, aud_tmp, final_out, offset)
            else:
                if os.path.exists(vid_tmp): os.replace(vid_tmp, final_out)
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            for f in [vid_tmp, aud_tmp]:
                if os.path.exists(f): 
                    try: os.remove(f)
                    except: pass
        self.recording_stopped.emit()

    def _merge_final(self, vid, aud, out, offset):
        ffmpeg_exe = _get_ffmpeg()
        dur = self._video_duration
        cmd = [
            ffmpeg_exe, '-y', '-ss', f'{offset:.4f}', '-i', aud, '-i', vid,
            '-c:v', 'copy', '-c:a', 'aac', '-t', f'{dur:.4f}', '-progress', 'pipe:1', out
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        total_us = int(dur * 1000000)
        for line in proc.stdout:
            if "out_time_us=" in line:
                try:
                    us = int(line.split('=')[1])
                    self.progress_updated.emit(min(int(us / total_us * 100), 99))
                except: pass
        proc.wait()
        self.progress_updated.emit(100)

    def stop(self): 
        self.is_recording = False
    def pause(self):
        self.is_paused = not self.is_paused
        if self._audio_rec: self._audio_rec.pause()
