# ContactsExporter
exports all google contacts and embeds contact icons

this program was tested with python 3.12 on linux mint

install the required libraries with

`pip install google-auth google-auth-oauthlib google-api-python-client requests`

how to use:
1. navigate to the same directory as the script and open a terminal
2. run `python ContactsExporter.py`
3. authenticate to the web browser that pops open
4. after the script finishes, navigate to `generated_vcards`, and there you have it! `all_contacts.vcf` should be in the folder, ready to import into some sort of contacts manager. 
