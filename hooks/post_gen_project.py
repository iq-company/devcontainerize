# import os import shutil
# 
# target = ".devcontainer"
# template = ".devcontainer_tpl"
# 
# if os.path.exists(target):
#     response = input(f"{target} existiert bereits. Überschreiben? [y/N] ").strip().lower()
#     if response != "y":
#         print("Abbruch.")
#         exit(1)
#     shutil.rmtree(target)
# 
# shutil.move(template, target)
# print(f"{target} wurde erfolgreich eingerichtet.")
# 
