# wiz-gcp-projectc-based-subs-tags
Assign  subscriptions based on Tags to wiz Project

# IMPORTANT: update the bellow variables on main.py  before running the script. The following fields are currently empty and need to be updated:
```
wiz_config_file --> Patch of the wiz config file
tag_key --> The tag that should be used to map the subscription to the Wiz Project
project_name_prefix --> Specify the project name prefix you want to append to the tag_value. The project_name will equal to  project_name_prefix+tag_value
```

## Prerequisites:
- The script is tested on Python 3.10
- Install gql, aiohttp and requests packages
    
## Applicable use cases:
- The purpose of the script is to have dynamic adding of P subscriptions to Wiz Projects based on Tags. This is to make sure that all onboarded subscriptions are automatically mapped to proper Wiz Projects. The script can be run on a regular basis (e.g. daily) to constantly update the accounts.
- There are 4 scripts on the folder. 
```
all-csp.py for all cloud provider. You can use this script if you have the same tagging strategy across CSPs
In case each CSP is using a different tag key then you can use the script related to the CSP.
The difference between all the script is the variable inside the function get_subs_with_tag_key ().
for example in the case of Azure it is 

                    "where": {
                        "cloudPlatform": {
                            "EQUALS": [
                                "Azure"
                            ]
                        },
                        "tags": {
                            "TAG_CONTAINS_ALL": [
                            {
                                "key": tag_key
                            }
                            ]
                        }
                    }
```

## Usage:
- dry-run to test which projects will be created and which subscriptions will be added to the Wiz Project.
```
python3 gcp.py --dry-run yes
```
- Run the script.
``` 
python3 gcp.py
```

