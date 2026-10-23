# Douyin Creator Knowledge Base

Turn one Douyin creator's full body of work into a distilled knowledge base. Use this skill when the user asks to watch, read, or learn everything from a Douyin account and keep it as structured notes.

## Set up the workspace

- Create a project folder with a files folder for lists, audio, transcripts, and finished documents, plus a hidden folder for scripts and logs.

- Reuse the existing transcription environment instead of installing fresh tools. The verified setup is a Python virtual environment under the home directory holding faster-whisper, a local faster-whisper small model directory, and ffmpeg on the system path.

- Install every tool under the home directory. System level installs do not survive virtual machine replacement, so never rely on a tool placed outside the home directory.

- Copy the two helper scripts from the scripts folder beside this file into the new project, then adapt the path constants at the top of each script to the new project. The scripts are `scripts/tikvid_batch.py` for downloading and `scripts/transcribe.py` for transcription.

## Collect the complete work list

- Build the full work list from the creator homepage before downloading anything, and keep collecting until the count matches the homepage total.

- Record one line per work with a serial number, the title, and the link, in homepage order.

- Include graphic text posts as their own items. They carry no audio, so fetch their text separately instead of counting them as download failures.

- Copy titles verbatim, including suspected typos or missing characters, and flag the anomaly beside the entry instead of silently fixing it.

- Confirm the interaction policy with the user before starting. The default from the verified run is read only, meaning no liking, no commenting, no following, and no direct messages.

## Download the audio with TikVid

- Use TikVid as the download route. It needs no login and no cookies.

- Send a POST request to https://tikvid.io/api/ajaxSearch with a desktop Chrome user agent, a Referer of https://tikvid.io/en, and a header of X-Requested-With set to XMLHttpRequest. Send form fields q set to the Douyin link and lang set to en.

- Read the Download MP3 anchor href out of the returned HTML with a real HTML parser and use the href verbatim. Do not extract it with a regular expression over raw HTML, because that truncates links.

- Fetch the MP3 link with curl using the same user agent and referer. Do not use urllib for the fetch, because it hits IncompleteRead errors on these responses.

- Run strictly one video at a time, parse and download each video immediately because direct links may expire, and sleep a few seconds between videos. The verified run used 4 seconds.

- Stop the whole run at once on HTTP 429 or 403 from the parse endpoint and report the stop point. Never hammer the endpoint.

- Treat one video failing as one recorded failure and move on. A single failure may get one later retry, never a tight loop.

- Verify every file with ffprobe and count only files with duration above zero as successes.

- Do not spend time on the yt-dlp plus cookies route. In the verified run, Douyin programmatic requests failed there with timeouts and 403 responses even with a valid login, because the platform requires a browser generated signature. The same run also found TikWM, tenapi, pearktrue, oick, and iesdouyin dead.

- After the run, hash the audio files with md5sum and group byte identical files. Identical files from different videos usually mean the service returned the same music only audio for each, so keep those videos in the gap list instead of transcribing them repeatedly.

## Transcribe with faster-whisper

- Transcribe with the local faster-whisper small model on CPU with int8 compute, Chinese language, beam size 5, and VAD filtering on.

- Test on one file before the bulk run, and let the bulk run skip transcripts that already exist and exceed 50 bytes so it resumes cleanly.

- Write each transcript as the title line, a blank line, then the plain ASR text. ASR text has no punctuation and may carry homophone errors, so treat it as a draft rather than a quote source.

- Keep audio with no speech on the failure list with its cause. Do not force a transcript out of music only audio.

- Flag transcripts whose content does not match their title as suspected mismatches instead of summarizing them as if they matched.

- Count Chinese characters with a method that counts characters, not bytes. Under a C locale, wc -m counts bytes, which inflates the count about threefold for Chinese text.

## Distill the knowledge base

- Build one document with four parts, in this order: an overview of the creator and coverage, a topic index, one summary per covered work, and a complete gap list.

- Give each summary the serial number, the title, the link, topic words, and 3 to 5 key points.

- Count the topic distribution over covered works only, and report gap counts by class: not downloaded, graphic text not fetched, audio without transcript, and near empty transcript.

- Never present a gap as covered. Write the gap list in full, with serial numbers and causes.

- Keep any verbatim quote from a single work under 50 words, and mark uncertain content as uncertain instead of writing it firmly.

## Add a topic analysis when the user asks for one

- Separate what the creator teaches from what the creator actually does, and list the tension points between the two as their own section.

- Keep differing figures side by side when the creator states them differently in different works. Do not force them into one number.

- Label inference as inference and keep it apart from what the transcripts state.

- Tie every load bearing claim to a work serial number so the user can check it.

## Alternatives for better results

- When a video fails to parse, fall back to watching the original video directly and writing notes from it, provided the login state allows it.

- When the creator has only a handful of works, skip the batch script and run the same parse and download steps one by one.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.
