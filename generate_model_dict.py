import os
import json

language_code_dict = {
    "english" : "en",
    "hindi" : "hi",
    "gujarati" : "gu",
    "tamil" : "ta",
    "telugu" : "te"
}

model_dict = {}
main_folder = 'deployed_models'
curr_dir = os.getcwd()

for folder in os.listdir(main_folder):
    try:
        path = "{0}/{1}/{2}/{2}.pt".format(curr_dir,main_folder,folder)
        model_dict[language_code_dict[folder]] = path
    except Exception as e:
        print(e)

with open('model_dict.json', 'w') as json_file:
  json.dump(model_dict, json_file, indent=4)

    


