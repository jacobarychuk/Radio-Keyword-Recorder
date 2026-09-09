# Radio Keyword Recorder

This project records audio from an online radio stream on a schedule and sends each recording as an MP3 attachment via email using the Mailgun API.

Run the recorder in the background:

```bash
nohup python -u main.py &
```

Output is written to `nohup.out`.
