#!/usr/bin/env python3
"""Build a narrated 1080p walkthrough from real app captures and source excerpts.

macOS: python demo/build_video.py --screenshots ../deliverables/screenshots-v2
Requires Pillow, imageio-ffmpeg (or --ffmpeg), and macOS `say`.
No screen is fabricated. Missing required captures stop the build.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ASSIGNMENT = ROOT.parent
WIDTH, HEIGHT = 1920, 1080
BG = "#edf1f2"
DARK = "#14272c"
TEAL = "#087e78"
MUTED = "#52666c"
WHITE = "#ffffff"
FONT_PATHS = ["/System/Library/Fonts/Avenir Next.ttc", "/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
MONO_PATHS = ["/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/SFNSMono.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]


def font(size, mono=False):
    for path in MONO_PATHS if mono else FONT_PATHS:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def run(command, **kwargs):
    return subprocess.run([str(item) for item in command], check=True, **kwargs)


def text(draw, xy, value, size=28, fill=DARK, width=None, spacing=12, mono=False):
    face = font(size, mono)
    if width:
        lines = []
        for paragraph in value.split("\n"):
            line = ""
            for word in paragraph.split():
                candidate = (line + " " + word).strip()
                if draw.textlength(candidate, font=face) > width and line:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
        value = "\n".join(lines)
    draw.multiline_text(xy, value, font=face, fill=fill, spacing=spacing)


def base(chapter, index, count):
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 148), fill=DARK)
    draw.rectangle((0, 148, WIDTH, 154), fill=TEAL)
    text(draw, (52, 25), chapter["title"], 48, WHITE)
    text(draw, (54, 91), chapter["subtitle"], 23, "#b9d5d6")
    text(draw, (54, 1024), "WIND DECISION REPLAY  /  Running application and source walkthrough", 21, MUTED)
    text(draw, (1600, 1024), f"PART {chapter['part']}  ·  {index:02d} / {count:02d}", 21, MUTED)
    draw.rectangle((0, 1074, int(WIDTH * index / count), 1080), fill=TEAL)
    return image


def screenshot_frame(chapter, index, count, path):
    image = base(chapter, index, count)
    source = Image.open(path).convert("RGB")
    fitted = ImageOps.contain(source, (1816, 818), Image.Resampling.LANCZOS)
    x, y = (WIDTH-fitted.width)//2, 173 + (818-fitted.height)//2
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((x-2,y-2,x+fitted.width+2,y+fitted.height+2),radius=12,fill=WHITE,outline="#cfdbde",width=2)
    image.paste(fitted,(x,y))
    return image


def architecture_frame(chapter, index, count):
    image = base(chapter,index,count)
    draw = ImageDraw.Draw(image)
    items = [("ELEXON API", "WINDFOR + FUELHH", "Two real historical requests"), ("PYTHON PROVIDER", "Fetch + normalize", "Parallel requests, bounded retries"), ("MEMORY CACHE", "300 seconds / instance", "Refresh bypasses the interval"), ("FASTAPI", "One dataset epoch", "Decision, month, metadata, status"), ("REACT", "Immediate evidence", "Forecasts, actuals and accuracy")]
    for number, (title, line, detail) in enumerate(items):
        x = 52 + number*374
        draw.rounded_rectangle((x,330,x+322,595),radius=20,fill=WHITE,outline="#d6e0e2",width=2)
        text(draw,(x+24,358),title,25,TEAL)
        text(draw,(x+24,420),line,27,DARK,width=272)
        text(draw,(x+24,512),detail,22,MUTED,width=272)
        if number<4:
            draw.line((x+330,461,x+366,461),fill=TEAL,width=5)
            draw.polygon([(x+366,461),(x+353,452),(x+353,470)],fill=TEAL)
    text(draw,(64,706),"Real API data is primary. Calculations stay in Python.",36,DARK)
    text(draw,(64,780),"On upstream failure: retain the last good API epoch, or label the bundled fallback.",29,MUTED)
    text(draw,(64,859),"SQLite is an explicit failure fallback. It is not the normal data source.",29,TEAL)
    text(draw,(64,922),"January decision dates lead to delivery from 2 January to 1 February 2026",26,MUTED)
    return image


def code_frame(chapter,index,count,path,start_marker,end_marker,bullets):
    image = base(chapter,index,count)
    draw = ImageDraw.Draw(image)
    content = path.read_text()
    start = content.index(start_marker)
    end = content.index(end_marker,start) if end_marker else len(content)
    excerpt = content[start:end].rstrip().splitlines()
    draw.rounded_rectangle((52,192,1280,970),radius=18,fill=DARK)
    text(draw,(80,216),str(path.relative_to(ROOT)),22,"#8dc5c5",mono=True)
    y=268
    for line in excerpt:
        wrapped=textwrap.wrap(line,width=93,replace_whitespace=False,drop_whitespace=False) or [""]
        for portion in wrapped:
            if y>933:
                break
            fill="#9bd7c3" if portion.strip().startswith("#") else "#edf4f4"
            text(draw,(82,y),portion,21,fill,mono=True)
            y+=29
    y=245
    for heading,body in bullets:
        text(draw,(1330,y),heading,31,TEAL,width=520)
        text(draw,(1330,y+66),body,26,MUTED,width=520,spacing=10)
        y+=220
    return image


def tests_frame(chapter,index,count,workspace):
    image=base(chapter,index,count)
    draw=ImageDraw.Draw(image)
    interpreter=Path("/private/tmp/wdr-venv/bin/python")
    if not interpreter.exists():
        interpreter=Path(sys.executable)
    env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"}
    completed=run([interpreter,"-m","pytest","backend/tests","-q","-p","no:cacheprovider"],cwd=ROOT,env=env,capture_output=True,text=True)
    (workspace/"executed-test-output.txt").write_text(completed.stdout+completed.stderr)
    draw.rounded_rectangle((52,198,1868,477),radius=20,fill=DARK)
    text(draw,(88,234),"$ python -m pytest backend/tests -q",30,"#a3dacf",mono=True)
    output=completed.stdout.splitlines()
    summary=next((line for line in output if re.search(r"\d+ passed",line)),"Executed checks completed successfully")
    text(draw,(88,324),output[0] if output else "",23,WHITE,mono=True)
    text(draw,(88,397),summary,28,"#a3dacf",mono=True)
    node=Path("/Users/bishwajit/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
    node=str(node) if node.exists() else shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required to execute the frontend interaction checks.")
    frontend=run([node,ROOT/"frontend"/"node_modules"/"vitest"/"vitest.mjs","run","--cache=false","--fsModuleCache=false","--attachmentsDir",workspace/"frontend-attachments"],cwd=ROOT/"frontend",env={**env,"CI":"1","NO_COLOR":"1"},capture_output=True,text=True)
    frontend_output=re.sub(r"\x1b\[[0-9;]*m","",frontend.stdout+frontend.stderr)
    (workspace/"executed-frontend-test-output.txt").write_text(frontend_output)
    frontend_summary=next((line.strip() for line in frontend_output.splitlines() if re.search(r"Tests\s+\d+ passed",line)),"Frontend interaction checks completed successfully")
    files_summary=next((line.strip() for line in frontend_output.splitlines() if "Test Files" in line),"")
    draw.rounded_rectangle((52,507,1868,745),radius=20,fill=DARK)
    text(draw,(88,541),"$ vitest run",30,"#a3dacf",mono=True)
    text(draw,(88,614),files_summary,25,WHITE,mono=True)
    text(draw,(88,674),frontend_summary,28,"#a3dacf",mono=True)
    tests=[("Domain rules","Publication cutoff, complete actuals, common cohorts"),("API provider","Cache reuse, forced refresh, concurrency and failure"),("User workflow","Immediate actuals, accuracy and visible refresh state")]
    for i,(heading,body) in enumerate(tests):
        y=790+i*65
        text(draw,(86,y),heading,28,TEAL)
        text(draw,(422,y),body,28,DARK)
    return image


def delivery_frame(chapter,index,count):
    image=base(chapter,index,count)
    draw=ImageDraw.Draw(image)
    docker=(ROOT/"Dockerfile").read_text() if (ROOT/"Dockerfile").exists() else "Dockerfile is not available."
    draw.rounded_rectangle((52,205,1160,963),radius=18,fill=DARK)
    text(draw,(82,234),"Dockerfile · actual repository source",24,"#8dc5c5",mono=True)
    y=289
    for line in docker.splitlines():
        for portion in textwrap.wrap(line,width=83,replace_whitespace=False) or [""]:
            if y<930:
                text(draw,(82,y),portion,20,"#edf4f4",mono=True)
                y+=26
    text(draw,(1225,238),"Reviewable delivery",37,TEAL)
    bullets=["Immediate actuals + accuracy", "Two real Elexon API requests", "300 second instance cache", "Manual Refresh", "Explicit stale / fallback status", "Docker + Vercel deployment"]
    for i,line in enumerate(bullets):
        text(draw,(1232,337+i*80),f"{i+1:02d}  {line}",27,DARK,width=610)
    text(draw,(1230,858),"January 2026 scope. This video stays local.",27,MUTED,width=570)
    return image


def duration(ffmpeg,path):
    result=subprocess.run([ffmpeg,"-hide_banner","-i",str(path)],capture_output=True,text=True)
    match=re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)",result.stderr)
    if not match:
        raise RuntimeError(f"Cannot read audio duration: {path}")
    return int(match[1])*3600+int(match[2])*60+float(match[3])


def srt_time(seconds):
    milliseconds=round(seconds*1000)
    hours,milliseconds=divmod(milliseconds,3600000)
    minutes,milliseconds=divmod(milliseconds,60000)
    seconds,milliseconds=divmod(milliseconds,1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def caption_chunks(narration):
    words=narration.split()
    chunks=[" ".join(words[index:index+14]) for index in range(0,len(words),14)]
    if len(chunks)>1 and len(chunks[-1].split())<6:
        chunks[-2]+=" "+chunks.pop()
    return chunks


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screenshots",type=Path,default=ASSIGNMENT/"deliverables"/"screenshots-v2")
    parser.add_argument("--output",type=Path,default=ASSIGNMENT/"deliverables"/"wind-decision-replay-demo-v2.mp4")
    parser.add_argument("--ffmpeg")
    parser.add_argument("--voice",default="Daniel")
    parser.add_argument("--rate",type=int,default=156)
    parser.add_argument("--prepare-only",action="store_true")
    parser.add_argument("--audio-only",action="store_true")
    args=parser.parse_args()
    chapters=json.loads((ROOT/"demo"/"chapters.json").read_text())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    workspace=args.output.parent/f"{args.output.stem}-build"
    workspace.mkdir(exist_ok=True)
    narration_dir=workspace/"narration"
    narration_dir.mkdir(exist_ok=True)
    for chapter in chapters:
        path=narration_dir/f"{chapter['id']}.txt"
        content=chapter["narration"]+"\n"
        if not path.exists() or path.read_text()!=content:
            path.write_text(content)
    total_words=sum(len(chapter["narration"].split()) for chapter in chapters)
    print(f"Narration: {total_words} words, approximately {total_words/args.rate:.1f} minutes",flush=True)
    if args.prepare_only:
        return
    ffmpeg=args.ffmpeg or shutil.which("ffmpeg")
    if not ffmpeg:
        dependency=Path("/private/tmp/wdr-video-deps")
        if dependency.exists():
            sys.path.insert(0,str(dependency))
        import imageio_ffmpeg
        ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    if not shutil.which("say"):
        raise RuntimeError("This narration build uses macOS say. Supply recorded chapter audio or run on macOS.")
    if args.audio_only:
        parts={1:0.0,2:0.0}
        for chapter in chapters:
            audio=workspace/f"{chapter['id']}.aiff"
            narration=narration_dir/f"{chapter['id']}.txt"
            if not audio.exists() or audio.stat().st_mtime<narration.stat().st_mtime:
                run(["/usr/bin/say","-v",args.voice,"-r",args.rate,"-f",narration,"-o",audio],capture_output=True,text=True)
            length=duration(ffmpeg,audio)+0.85
            parts[chapter["part"]]+=length
            print(f"{chapter['id']}: {length:.2f}s",flush=True)
        print(json.dumps({"part_seconds":parts,"total_seconds":sum(parts.values())},indent=2))
        return
    required=[name for chapter in chapters for name in (chapter["visual"], chapter.get("visual_alt","")) if name.endswith(".png")]
    missing=[name for name in required if not (args.screenshots/name).exists()]
    if missing:
        raise RuntimeError("Missing actual app captures: "+", ".join(sorted(set(missing))))
    segments=[]
    elapsed=0.0
    part_lengths={1:0.0,2:0.0}
    captions=[]
    manifest=[]
    for index,chapter in enumerate(chapters,1):
        chapter=dict(chapter)
        if chapter["id"]=="04-revision-evidence" and not chapter.get("visual_alt"):
            # The overview proves immediate cards/status; the chart capture also
            # exposes the 6.3% revision result and its 24-hour comparison cohort.
            chapter.update(visual_alt="06-chart.png",switch_fraction=0.25)
        print(f"Building chapter {index}/{len(chapters)}: {chapter['title']}",flush=True)
        audio=workspace/f"{chapter['id']}.aiff"
        narration=narration_dir/f"{chapter['id']}.txt"
        if not audio.exists() or audio.stat().st_mtime<narration.stat().st_mtime:
            run(["/usr/bin/say","-v",args.voice,"-r",args.rate,"-f",narration,"-o",audio],capture_output=True,text=True)
        audio_duration=duration(ffmpeg,audio)
        clip_duration=audio_duration+0.85
        visual=chapter["visual"]
        if visual.endswith(".png"):
            frame=screenshot_frame(chapter,index,len(chapters),args.screenshots/visual)
        elif visual=="architecture":
            frame=architecture_frame(chapter,index,len(chapters))
        elif visual=="importer":
            frame=code_frame(chapter,index,len(chapters),ROOT/"backend"/"app"/"elexon.py",'    def _upstream(self):',"    def peek_status(self):",[("Two real API requests","Forecasts and actuals are fetched in parallel."),("300 second cache","Manual Refresh bypasses the interval."),("Honest failure state","Keep last good data; label any bundled fallback.")])
        elif visual=="selection":
            frame=code_frame(chapter,index,len(chapters),ROOT/"backend"/"app"/"analysis.py","    matched = [row for row in series",'    if change is not None and change > 0:',[("No look-ahead","Only published information enters the replay."),("Shared cohort","Both revisions are measured on the same target hours."),("Headline accuracy","All complete selected/actual matches remain visible.")])
        elif visual=="tests":
            frame=tests_frame(chapter,index,len(chapters),workspace)
        else:
            frame=delivery_frame(chapter,index,len(chapters))
        frame_path=workspace/f"{chapter['id']}.png"
        frame.save(frame_path)
        segment=workspace/f"{chapter['id']}.mp4"
        filters=f"fade=t=in:st=0:d=0.25,fade=t=out:st={max(0,clip_duration-0.25):.3f}:d=0.25,format=yuv420p"
        command=[ffmpeg,"-hide_banner","-loglevel","error","-y","-loop","1","-framerate","12","-i",frame_path]
        if chapter.get("visual_alt"):
            alternate=workspace/f"{chapter['id']}-detail.png"
            screenshot_frame(chapter,index,len(chapters),args.screenshots/chapter["visual_alt"]).save(alternate)
            command += ["-loop","1","-framerate","12","-i",alternate,"-i",audio,"-filter_complex",f"[0:v][1:v]overlay=enable='gte(t,{audio_duration*chapter.get('switch_fraction',0.65):.3f})',{filters}[v]","-map","[v]","-map","2:a"]
        else:
            command += ["-i",audio,"-vf",filters]
        command += ["-af","apad=pad_dur=0.85","-t",f"{clip_duration:.3f}","-r","24","-c:v","libx264","-preset","ultrafast","-tune","stillimage","-crf","23","-c:a","aac","-b:a","128k","-ar","48000",segment]
        run(command)
        segments.append(segment)
        chunks=caption_chunks(chapter["narration"])
        total_weight=sum(len(chunk.split()) for chunk in chunks)
        caption_at=elapsed
        for chunk in chunks:
            span=audio_duration*len(chunk.split())/total_weight
            captions.append((caption_at,caption_at+span,chunk))
            caption_at+=span
        manifest.append({"chapter":chapter["id"],"part":chapter["part"],"title":chapter["title"],"start_seconds":round(elapsed,3),"duration_seconds":round(clip_duration,3),"visual":visual,"visual_alt":chapter.get("visual_alt")})
        elapsed+=clip_duration
        part_lengths[chapter["part"]]+=clip_duration
    if elapsed>600 or any(value>300 for value in part_lengths.values()):
        raise RuntimeError(f"Video exceeds assignment limits: total {elapsed:.1f}s, parts {part_lengths}. Raise --rate.")
    caption_path=args.output.with_suffix(".srt")
    caption_path.write_text("\n\n".join(f"{i}\n{srt_time(start)} --> {srt_time(end)}\n{line}" for i,(start,end,line) in enumerate(captions,1))+"\n")
    concat=workspace/"concat.txt"
    concat.write_text("\n".join(f"file '{segment}'" for segment in segments)+"\n")
    ffmetadata=workspace/"chapters.ffmetadata"
    ffmetadata.write_text(";FFMETADATA1\ntitle=Wind Decision Replay\ncomment=Actual application captures and source excerpts with disclosed synthetic narration.\n"+"".join(f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={round(item['start_seconds']*1000)}\nEND={round((item['start_seconds']+item['duration_seconds'])*1000)}\ntitle=Part {item['part']} - {item['title']}\n" for item in manifest))
    run([ffmpeg,"-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",concat,"-i",caption_path,"-i",ffmetadata,"-map","0:v","-map","0:a","-map","1:0","-map_metadata","2","-map_chapters","2","-c:v","copy","-c:a","copy","-c:s","mov_text","-metadata:s:s:0","language=eng","-movflags","+faststart",args.output])
    report={"output":str(args.output),"duration_seconds":round(elapsed,3),"part_durations_seconds":part_lengths,"words":total_words,"voice":args.voice,"speech_rate":args.rate,"synthetic_narration":True,"created_at":datetime.now(timezone.utc).isoformat(),"chapters":manifest}
    args.output.with_name(f"{args.output.stem}-manifest.json").write_text(json.dumps(report,indent=2)+"\n")
    chapter_lines=[]
    for item in manifest:
        seconds=int(item["start_seconds"])
        chapter_lines.append(f"{seconds//60:02d}:{seconds%60:02d} {item['title']}")
    description="Wind Decision Replay — local walkthrough version 2\n\nA historical wind forecast pilot for a UK electricity buying team. Actuals and accuracy are immediately visible. The provider fetches the two real Elexon APIs, uses a 300 second instance cache, supports manual Refresh, and labels stale or bundled fallback data explicitly. The first part demonstrates the customer workflow; the second explains the architecture, data rules, calculations, and verification.\n\n"+"\n".join(chapter_lines)+"\n\nThe walkthrough uses screenshots of the running React and Python application and actual repository source excerpts. Narration is generated using the macOS Daniel synthetic voice. AI assistance is disclosed in the repository README. The video remains local; it has not been uploaded or submitted.\n\nData: Elexon WINDFOR forecasts and FUELHH WIND actuals. January 2026 decision dates; next-day delivery from 2 January to 1 February. This pilot evaluates wind forecast mismatch, not customer demand, procurement requirements, or financial profit.\n"
    args.output.with_name(f"{args.output.stem}-description.txt").write_text(description)
    print(json.dumps(report,indent=2),flush=True)


if __name__=="__main__":
    main()
