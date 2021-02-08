import inotify.adapters
import os
from upload_to_google import set_gcs_credentials, upload_file

notifier = inotify.adapters.Inotify()
set_gcs_credentials()
if not os.path.exists('utterances'):
    os.system('mkdir utterances')

notifier.add_watch('utterances')

for event in notifier.event_gen(yield_nones=False):
    if event is not None:
        (_, type_names, path, filename) = event
        if len(filename) != 0:
            if 'IN_CLOSE_WRITE' in type_names:
                file_name_split = filename.split("__")
                user_id = file_name_split[0]
                language = file_name_split[-1].replace(".wav","").replace(".txt","")

                upload_file(user_id, filename, path, language)

                os.remove(path+"/"+filename)


