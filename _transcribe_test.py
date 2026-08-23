import os, sys, stat
sys.path.insert(0, os.getcwd())
from app.voice.speech_recognition import SpeechRecognitionThread

tmp = os.path.join(os.path.abspath(os.getcwd()), "_whisper_stubs")
os.makedirs(tmp, exist_ok=True)

model = os.path.join(tmp, "fake-model.bin")
open(model, "w").write("x")

# Mirror real whisper.cpp -otxt format: bracketed [start --> end] per segment.
fake_bin = os.path.join(tmp, "whisper")
stub_src = r'''#!/usr/bin/env python3
import sys, os
pfx = None
args = sys.argv[1:]
i = 0
while i < len(args):
    if args[i] == "-of" and i + 1 < len(args):
        pfx = args[i + 1]; i += 2; continue
    i += 1
if pfx:
    with open(pfx + ".txt", "w") as out:
        out.write("[0:0:0.0 --> 0:0:2.500] open a new tab\n"
                  "[0:0:02.500 --> 0:0:04.000] click 【tok】\n")
'''
with open(fake_bin, "w") as f:
    f.write(stub_src)
os.chmod(fake_bin, stat.S_IRWXU)
os.environ["PATH"] = tmp + os.pathsep + os.environ["PATH"]

t = SpeechRecognitionThread(model_path=model, whisper_bin=fake_bin, language="en")
text = t._transcribe(b"\x00\x00" * 800)
print("cleaned:", repr(text))
assert text == "open a new tab click", f"cleaning failed: {text!r}"
print("OK: whisper.cpp -otxt timestamps + 【special】 brackets stripped; transcript joined")
