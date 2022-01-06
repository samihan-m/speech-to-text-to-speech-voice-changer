# import requests
import aiohttp
import asyncio

async def get_voiceover(text_to_say, audio_count):
    """
    From a text string, returns the audio file of a 15.ai character speaking the text
    """
    return await download_voiceover(await request_voiceover(text_to_say, audio_count), audio_count)

async def request_voiceover(text_to_say, audio_count):
    """
    Given text to say, requests a voice clip from 15.ai
    Returns the URL to the voice clip
    """

    # this process is specific to the 15.ai API
    voiceover_post_url = "https://api.15.ai/app/getAudioFile5"
    global character_name
    voiceover_info = {"text": text_to_say, "character": character_name, "emotion":"Contextual"}

    async with aiohttp.ClientSession() as session:

        best_voiceover = None

        while best_voiceover is None:
            try:
                print(f"Requesting voiceover for Audio #{audio_count}")
                async with session.post(voiceover_post_url, json=voiceover_info) as response:
                    post_response = await response.json(content_type=None)
                    best_voiceover = post_response['wavNames'][0]
            except Exception as error:
                print("Error encountered during post request. Retrying.")
                print(error)

    voiceover_get_url = f"https://cdn.15.ai/audio/{best_voiceover}"
    return voiceover_get_url

async def download_voiceover(download_url, audio_count):
    """
    Given a download URL, downloads the file and returns it
    """
    async with aiohttp.ClientSession() as session:
        audio_file = None
        while audio_file is None:
            try:
                print(f"Getting voiceover for Audio #{audio_count}")
                async with session.get(download_url) as response:
                    audio_file = await response.read()
            except Exception as error:
                print("Error encountered during get request. Retrying.")
                print(error)
    return audio_file

import sounddevice as sd
import soundfile as sf
import io

LOOPED_BACK_OUTPUT = "Line 1 (Virtual Audio Cable), MME"

def play_audio(audio_data):
    """
    Plays the audio provided by the audio_data through both the microphone Line 1 and the default headphones
    """

    data, sample_rate = sf.read(io.BytesIO(audio_data), dtype="float32")
    loopback_stream = sd.OutputStream(device=LOOPED_BACK_OUTPUT, channels=data.ndim)
    headphones_stream = sd.OutputStream(channels=data.ndim)
    loopback_stream.start()
    headphones_stream.start()
    loopback_stream.write(data)
    headphones_stream.write(data)

import speech_recognition as sr
import re
from num2words import num2words

character_name = "Spy"

def change_character(name):
    """
    Given a name, change the character_name to a new value according to the characters dictionary which maps more easily voiced names to official names
    """
    global character_name
    characters = {
        "gladys": "GLaDOS",
        "glados": "GLaDOS",
        "spy": "Spy", 
        "spongebob": "SpongeBob SquarePants", 
        "pony": "Twilight Sparkle",
        "narrator": "The Narrator",
        "q": "Kyu Sugardust",
        "queue": "Kyu Sugardust",
        "rise": "Rise Kujikawa"
    }
    character_name = characters.get(name.lower(), character_name)
    print(f"Set character_name to {character_name}")

do_use_voiceover = True

def toggle_voiceover(args):
    """
    Toggles outgoing audio between voiceover playbacks and normal microphone
    Accepts args as params because if there are any words after the command phrase this will throw error because it will pass a param
    """
    global do_use_voiceover
    do_use_voiceover = not do_use_voiceover
    if do_use_voiceover is True:
        print(f"Now using voiceover playback")
    else:
        print(f"Now using normal microphone")

import time

# list of timestamps of voiceover fetch requests
queued_voiceovers = []

# list of available voice commands. keys are activation phrases and values are functions for those commands
commands = {
    "command change voice to": change_character,
    "command toggle": toggle_voiceover
}

def transcribe_audio_threaded(audio, audio_count):
    """
    Processes the given audio data, then calls functions to fetch a voiceover audio and play that audio once fetched.
    """
    transcribed_text = None
    r = sr.Recognizer()
    # recognize speech using Google Speech Recognition
    try:
        transcribed_text = r.recognize_google(audio)
        # remove numbers from the text and replace them with words
        transcribed_text = re.sub(r"(\d+)", lambda x: num2words(int(x.group(0))), transcribed_text)
        print(f"Transcribed Audio #{audio_count}: \"{transcribed_text}\"")

        # check for commands
        for key in commands.keys():
            if transcribed_text.startswith(key):
                print(f"Command: {key}")
                args = transcribed_text[len(key):].strip()
                print(f"Args: {args}")
                commands[key](args)
                # Don't play a voiceover for a command, so exit before the voiceover is fetched
                return

        # generate an ID for each voiceover request so we can keep track of them before they are played
        voiceover_request_id = time.time()
        queued_voiceovers.append(voiceover_request_id)
        audio_byte_stream = None
        if do_use_voiceover is True:
            audio_byte_stream = asyncio.run(get_voiceover(transcribed_text, audio_count))
        else:
            audio_byte_stream = audio.get_wav_data()
        # block play_audio until the audio file play_audio should play has no preceding lines to play (even ones in the process of being downloaded)
        while [voiceover for voiceover in queued_voiceovers if voiceover < voiceover_request_id]:
            continue
        print(f'Playing {"voiceover" if do_use_voiceover else "microphone input"} for Audio #{audio_count}')
        play_audio(audio_byte_stream)
        queued_voiceovers.remove(voiceover_request_id)
        end_time = time.time()
        end_times[audio_count] = end_time
        end_thread(audio_count)
        return
    except sr.UnknownValueError:
        print("Could not understand audio")
    except sr.RequestError as e:
        print("Could not request results from Google Speech Recognition service; {0}".format(e))

    # End audio processing thread, indicate it was an error
    end_time = -1
    end_times[audio_count] = end_time
    end_thread(audio_count)
    return

start_times = {}
end_times = {}
average_response_time = 0
finished_responses = 0

def end_thread(audio_count):
    """
    Prints how long it took for the audio processing thread to execute (from audio enqueue to line being played)
    """
    if end_times[audio_count] == -1:
        print(f"Audio #{audio_count} contains nothing to process.")
        pass
    else:
        global average_response_time
        global finished_responses
        response_time = end_times[audio_count] - start_times[audio_count]
        average_response_time = (average_response_time*finished_responses + response_time)/(finished_responses + 1)
        finished_responses += 1
        print(f"Audio #{audio_count} took {response_time} seconds to finish.")
        print(f"Average response time: {average_response_time}")


# This is useless because how do I call it?? LOL
def get_average_response_time():
    """
    Using end_times and start_times (excluding end_times for unrecognizable audio), returns the average response time between audio enqueueing and voiceover playback
    """
    response_times = []
    for i in range(0, len(start_times)):
        if end_times[i] != -1:
            response_times.append(end_times[i] - start_times[i])
    average_response_time = sum(response_times)/len(response_times)
    print(f"The average response time of the program has been {average_response_time}")
    return average_response_time

# Counter of how many audios have been processed
audio_count = 0
# List of audio to be processed
queued_audio = []
def enqueue_audio(recognizer, audio):
    """
    Appends the audio to the queue of audio to be processed
    """
    global audio_count
    audio_count += 1
    print(f"Enqueuing Audio #{audio_count}")
    queued_audio.append(audio)
    start_time = time.time()
    start_times[audio_count] = start_time

from threading import Thread

def main():
    """
    In a loop, listens for microphone input, then plays a text-to-speech version of the input back to user and through a second output (ideally user's microphone).
    The name of the second output to be used is defined by LOOPED_BACK_OUTPUT, which ideally loops back to the microphone if virtual audio cable is configured correctly
    """

    # TODO
    # Block audio playback until all preceding threads START audio playback
    r = sr.Recognizer()
    default_mic = sr.Microphone()
    with default_mic as source:
        r.adjust_for_ambient_noise(source, duration=3)
        r.dynamic_energy_threshold = True
    print("Listening...")

    stop_listening = r.listen_in_background(source, enqueue_audio, phrase_time_limit=7)
    while True:
        if queued_audio:
            audio = queued_audio.pop(0)
            thread = Thread(target = transcribe_audio_threaded, args = (audio, audio_count))
            thread.start()
        continue


if __name__ == "__main__":
    main()