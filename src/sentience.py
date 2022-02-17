import csv
import logging
import random

import discord
from discord.ext import commands
from thefuzz import fuzz
import asyncio

class _Common:

    def import_csv_to_dict(self, file_name):
        with open(file_name, 'r') as f:
            reader = csv.DictReader(f)
            dict_of_columns = {}
            for row in reader:
                for column in row:
                    if row[column] != '':
                        if column not in dict_of_columns:
                            dict_of_columns[column] = [row[column]]
                        else:
                            dict_of_columns[column].append(row[column])
        return dict_of_columns

    def compare_string_fuzzy(self, string, list_of_strings):
        scores = []
        for item in list_of_strings:
            score = fuzz.ratio(string, item)
            scores.append(score)
        return scores

    def __init__(self):
        self.__emotional_phrase_list = self.import_csv_to_dict(
            'src/data/emotional_phrase_list.csv')
        self.mean_phrases = self.__emotional_phrase_list['mean_phrases']
        self.nice_phrases = self.__emotional_phrase_list['nice_phrases']


class Rating():
    """ This class handles emotional ratings for input phrases. """
    # initialize the class

    def __init__(self):
        self.__common = _Common()
        self.mean_phrases = self.__common.mean_phrases
        self.nice_phrases = self.__common.nice_phrases

    def rate_string_emotion(self, string):
        mean_scores = self.__common.compare_string_fuzzy(
            string, self.__common.mean_phrases)
        nice_scores = self.__common.compare_string_fuzzy(
            string, self.__common.nice_phrases)
        mean_score = max(mean_scores)
        nice_score = max(nice_scores)
        if mean_score < 55 and nice_score < 55:
            if mean_score > nice_score:
                return 'Confusing', f'{mean_score} mean'
            else:
                return 'Confusing', f'{nice_score} nice'
        # return the highest confidence score
        elif mean_score > nice_score:
            return 'Mean', mean_score
        elif nice_score > mean_score:
            return 'Nice', nice_score


class ResponseObject():
    """This object contains responses to the user."""
    # initialize the class

    def __init__(self, responses_filename: str):
        __response_list = _Common().import_csv_to_dict(responses_filename)
        self.nice = __response_list['nice_responses']
        self.mean = __response_list['mean_responses']
        self.confused = __response_list['confused_responses']


async def sentience_response(message: discord.Message, text: str):
    rating = Rating()
    response_object = ResponseObject('src/data/responses.csv')
    response_type = rating.rate_string_emotion(text)[0]
    if response_type == 'Mean':
        async with message.channel.typing():
            response = random.choice(response_object.mean)
            # wait for 1 to 3 seconds
            await asyncio.sleep(random.randint(1, 3))
    elif response_type == 'Nice':
        async with message.channel.typing():
            response = random.choice(response_object.mean)
            # wait for 1 to 3 seconds
            await asyncio.sleep(random.randint(1, 3))
    else:
        await asyncio.sleep(random.randint(2, 5))
        await message.add_reaction("👀")
        return
    await message.reply(response, mention_author=False)
