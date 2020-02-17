import os
import math

import dash
import dash_html_components as html
import dash_core_components as dcc
import numpy as np
import pandas as pd
import plotly.express as px
import speech_recognition as sr

from pydub import AudioSegment


PATH = "assets/pmoney.mp3"
podcast = AudioSegment.from_mp3(PATH)
PODCAST_LENGTH = podcast.duration_seconds
PODCAST_INTERVAL = 5000

app = dash.Dash(__name__)
server = app.server


def seconds_to_MMSS(slider_seconds):
    decimal, minutes = math.modf(slider_seconds / 60.0)
    seconds = str(round(decimal * 60.0))
    if len(seconds) == 1:
        seconds = "0" + seconds
    MMSS = "{0}:{1}".format(round(minutes), seconds)
    return MMSS


def generate_plot(step=1):
    print(PODCAST_INTERVAL * step, PODCAST_INTERVAL * (step + 1))
    # 5 second interval of podcast
    seg = podcast[PODCAST_INTERVAL * step: PODCAST_INTERVAL * (step + 1)]
    samples = seg.get_array_of_samples()
    arr = np.array(samples)
    df = pd.DataFrame(arr)
    fig = px.line(df, x=df.index, y=0, render_mode="webgl")
    fig.update_layout(
        height=250,
        margin_r=0,
        margin_l=0,
        margin_t=0,
        yaxis_title="",
        yaxis_fixedrange=True,
    )

    # Set custom x-axis labels
    fig.update_xaxes(
        ticktext=[seconds_to_MMSS(i + step * 5) for i in range(6)],
        tickvals=[i * 100000 for i in range(6)],
        tickmode="array",
        title="",
    )

    return fig


fig = generate_plot()

app.layout = html.Div(
    [
        html.H4(children="AI Speech Recognition (Planet Money podcast)"),
        dcc.Markdown(
            "Written in 100 lines of Python with [Dash](https://dash.plot.ly/)."
        ),
        dcc.Markdown(
            """
    **Instructions:** Drag the blue slider to transcribe audio from a Planet \
        Money podcast (in 5 second increments.) Transcription is done \
            in realtime with Python bindings to [Carnegie Mellon's \
                Sphinx Speech Recognition software](https://cmusphinx.github.io). \
                    Play the audio to see how well the transcription matches.
    [Code on GitHub](https://github.com/jackparmer/dashdub).
    """
        ),
        dcc.Markdown("**Drag this slider** (then wait a few seconds):"),
        dcc.Slider(id="my-slider", min=0, max=1155, step=5, value=0),
        html.Div(id="slider-output-container"),
        html.P(children="Carnegie Mellon Sphinx transcription:"),
        dcc.Textarea(id="transcription_output", cols=80),
        html.Br(),
        html.Audio(id="player", src=PATH, controls=True, style={
            "width": "100%"
        }),
        dcc.Graph(id="waveform", figure=fig),
    ]
)


#  Transcribe audio
@app.callback(
    [
        dash.dependencies.Output("slider-output-container", "children"),
        dash.dependencies.Output("waveform", "figure"),
        dash.dependencies.Output("transcription_output", "value"),
        dash.dependencies.Output("player", "src"),
    ],
    [dash.dependencies.Input("my-slider", "value")],
)
def transcribe_audio(slider_seconds):

    # Update MM:SS display
    MMSS = 'You are at minute "{0}"'.format(seconds_to_MMSS(slider_seconds))

    # Update graph
    step = round(slider_seconds / 5)
    fig = generate_plot(step)

    # Transcribe 5 seconds of audio
    seg = podcast[PODCAST_INTERVAL * (step - 1): PODCAST_INTERVAL * step]
    f = seg.export(out_f=None, format="wav")

    # Use URI timerange property to seek to correct position in HTML Audio
    # https://stackoverflow.com/a/36368454
    src = PATH + "#t=" + str(max(0, slider_seconds - 5))

    # pydub's export returns a BufferedRandom (BR) object
    # https://github.com/jiaaro/pydub/blob/master/pydub/audio_segment.py#L766
    # seek to the beginning of the BR so that speech_recognition's AudioFile can read it:
    # https://github.com/Uberi/speech_recognition/blob/master/speech_recognition/__init__.py#L209

    f.seek(0)
    r = sr.Recognizer()
    with sr.AudioFile(f) as source:
        audio = r.record(source)  # read the entire audio file

    try:
        transcription = r.recognize_sphinx(audio)
    except Exception as e:
        print(e)
        transcription = ""

    return MMSS, fig, transcription, src


if __name__ == "__main__":
    app.run_server(debug=True, host='0.0.0.0', port=os.getenv('PORT', 8500))
