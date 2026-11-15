"""Make the voice line with the local Kokoro speech model, and write the timing of each word and its phonemes.

Usage: ~/tools/tts/.venv/bin/python scripts/v6_speech.py <out.wav> <out.json> [voice]
"""
import sys, json, numpy as np, soundfile as sf
from kokoro import KPipeline

out_wav, out_json = sys.argv[1], sys.argv[2]
voice = sys.argv[3] if len(sys.argv) > 3 else "am_michael"
TEXT = ("Hello! I am Professor Torque. Welcome to Tiny Torque. "
        "Tiny machines, real satisfaction! Today, we will see how a gear works.")
pipe = KPipeline(lang_code="b" if voice.startswith("b") else "a")
SR = 24000; audio = []; words = []; t0 = 0.0
for res in pipe(TEXT, voice=voice, speed=0.95, split_pattern=r"(?<=[.!?])\s+"):
    a = res.audio.cpu().numpy() if hasattr(res.audio, "cpu") else np.asarray(res.audio)
    for tk in (res.tokens or []):
        if tk.start_ts is None or tk.end_ts is None or not tk.phonemes: continue
        words.append({"text": tk.text, "phonemes": tk.phonemes, "start": round(t0 + float(tk.start_ts), 3), "end": round(t0 + float(tk.end_ts), 3)})
    audio.append(a); audio.append(np.zeros(int(SR * 0.28), dtype=a.dtype)); t0 += len(a) / SR + 0.28
audio = np.concatenate([np.zeros(int(SR * 0.5), dtype=audio[0].dtype)] + audio + [np.zeros(int(SR * 0.8), dtype=audio[0].dtype)])
for w in words: w["start"] += 0.5; w["end"] += 0.5
peak = float(np.abs(audio).max()); audio = audio / peak * 0.89
sf.write(out_wav, audio, SR, subtype="PCM_16")
json.dump({"text": TEXT, "voice": voice, "sample_rate": SR, "duration": round(len(audio) / SR, 3), "words": words}, open(out_json, "w"), indent=1, ensure_ascii=False)
print("WROTE", out_wav, "seconds", round(len(audio) / SR, 2), "words", len(words))
for w in words: print(f'  {w["start"]:6.2f}-{w["end"]:6.2f}  {w["text"]:14s} {w["phonemes"]}')
