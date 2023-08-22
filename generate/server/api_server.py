# This is a minimal Flask-based Web server for the three-system
# story generator.

#import torch.multiprocessing as mp
# import nltk

import argparse

from flask import Flask
from flask import jsonify
from flask import request
from flask import render_template
from flask_cors import CORS
from flask_classful import FlaskView, route

import time, os
import json

import system1_sampling as system1

app=Flask(__name__)
CORS(app) # Make the browser happier about cross-domain references.

# Tell the browser to discard cached static files after
# 300 seconds.  This will facilitate rapid development
# (for even more rapid development, set the value lower).
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 300

STORY_TEMP = 0.5
MAX_LEN = 100
TOPIC = ''
SUBSTITUTION_DIC = {
    "&lt;unk&gt;": "<unk>",
    " &#x27;ve": "'ve",
    " ' ve": "'ve",
    " &#x27;m": "'m",
    " ' m": "'m",
    " &#x27;re": "'re",
    " ' re": "'re",
    " n&#x27;t": "n't",
    " &#x27;s": "'s",
    " ' s": "'s",
    "&#x27;": "'",
    " ,": ",",
    " .": "."
}

UNK_PLEASURES = {
    "&lt;": "<",
    "&gt;": ">",
    "&#x27;": "'",
    ".": ". </s>",
    "?": ". </s>",
    "!": ". </s>"
}


class StoryView(FlaskView):
    """A classful Flask REST server serving GPT2 generated stories based on user
    inputs. Uses classful Flask so the story generator can persist during
    runtime, rather than having to reload every time an API call is made.
    """

    def __init__(self):
        self.gen = system1.System1_Generator("Unthank")

    @route('/api/story')
    def generate(self):
        # http://localhost:5000/
        topic = request.values.get("topic", TOPIC)

        story_temp = request.values.get("story_temp", STORY_TEMP)
        if str(story_temp).upper() == "NONE":
            story_temp = None
        elif str(story_temp) == "":
            story_temp = STORY_TEMP
        else:
            story_temp = float(story_temp)
            if story_temp == 0.0: # Protect against divide-by-zero.
                story_temp = 0.001
        print(f"story temp is {story_temp}")

        max_len = request.values.get("max_len", "")
        if max_len.upper() == "NONE":
            max_len = MAX_LEN
        elif max_len == "":
            max_len = MAX_LEN
        else:
            max_len = int(max_len)
        print(f"Maximum length is {max_len}")

        response = self.gen.generate_response(
            topic=topic,
            kw_temp=None,
            story_temp=story_temp,
            dedup=None,
            max_len=max_len,
            use_gold_titles=None,
            oov_handling=None
        )
        response = preprocess(response, UNK_PLEASURES)
        fileify(topic, story_temp, max_len, response, True)
        fileify(topic, story_temp, max_len, response, False)
        return response
        #return jsonify(response)

StoryView.register(app,route_base = '/')

def preprocess(story, substitution_dic):
    """Uses a sustitution dictionary to correct for artefacts of the generation
    system.

    params:
        story:  The string generated by the generation system, raw.
        substitution_dic:   Dictionary containing substrings and their
                substitutions. Python now has ordered dicts, which may be used
                to control the output of preprocessing

    returns:
        story:  The story generated my the generation system, cleaned up a bit.
    """
    for pattern, replacement in substitution_dic.items():
        story = story.replace(pattern, replacement)
    # for line in story_lines:
    #     pass // this
    return story

def fileify(topic, story_temp, max_len, response, make_json):
    """Saves a record of the system's inputs and output to a file: either human-
    readable txt, or machine-readable json"""
    t = time.localtime()
    # uses time and date to ensure uniqueness of logfiles
    filename = f"logs/{t.tm_year}_{t.tm_mon}_{t.tm_mday}_{t.tm_hour}_{t.tm_min}_{t.tm_sec}_story.{'json' if make_json else 'txt'}"
    # create a log folder if none exists
    if not os.path.isdir('logs'):
        os.mkdir('logs')
    with open(filename, 'w') as file:
        if make_json:
            file.write(
                json.dumps(
                    {
                        "topic": topic,
                        "story_temp": story_temp,
                        "max_len": max_len,
                        "response": response
                    }
                )
            )
        else:
            file.write(f"PROMPT: {topic}\n")
            file.write(f"STORY_TEMP: {story_temp}\n")
            file.write(f"MAX_LEN: {max_len}\n")
            file.write("\nREPONSE\n\n")
            file.write(response)


if __name__ == '__main__':
    app.run(debug=False)
