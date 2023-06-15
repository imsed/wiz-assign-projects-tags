# © 2022 Wiz, Inc.
# This software is provided as-as and is covered under the Wiz MSA
# which can be found at https://www.wiz.io/legal/master-subscription-agreement

# Python 3.6+
# pip install dryable, requests

import argparse
import dryable
import json
import os
import requests
import sys
import traceback



############### Start Script settings ###############

# Using a config file to store credential information
# We default to checking for a config file FIRST
# and then fall back to checking for environment vars
# Default will be skipped, update with real path to config file
wiz_config_file = ""

# Specify the tag_key that will include the project information 
tag_key = ""

# Specify the project name prefix you want to append to the tag_value. 
# The project_name will equal to <project_name_prefix+tag_value>

project_name_prefix = ""

# You can run the script with the dry-run option set to yes
dryable.set( '--dry-run' in sys.argv and 'yes' in sys.argv)

# Define the argument and help of the script
parser=argparse.ArgumentParser(
    description='''Assign  subscriptions based on tags to wiz Projects ''',
    epilog="""All is well that ends well.""")
parser.add_argument('--dry-run', choices =['yes','no'], default='no', help='dry run, will not create new Wiz project and will not assign  subscriptions to WIZ projects')
args=parser.parse_args()

############### End Script settings ###############

############### Start Helpers ###############

def print_logo() -> None:
    """
    Print out the Wiz logo and script information

    Parameters:
        - none

    Returns:
        - none
    """

    print(
        f"""
                    __      _(_)____  ✦  ✦                                    
                    \ \ /\ / / |_  /    ✦                                     
                     \ V  V /| |/ /                                           
                      \_/\_/ |_/___|      
+----------------------------------------------------------------------+
  WIZ API ENDPOINT: {WIZ_API_URL} | AUTH URL: {WIZ_AUTH_URL} 
+----------------------------------------------------------------------+
      SCRIPT NAME: {SCRIPT_NAME} | © 2023 Wiz, Inc. 
+----------------------------------------------------------------------+
  {SCRIPT_DESCRIPTION}
+----------------------------------------------------------------------+"""
    )


def _generic_exception_handler(function):
    """
    Private decorator function for error handling

    Parameters:
        - function: the function to pass in

    Returns:
        - _inner_function: the decorated function
    """

    def _inner_function(*args, **kwargs):
        try:
            function_result = function(*args, **kwargs)
            return function_result
        except ValueError as v_err:
            print(traceback.format_exc(), f"{v_err}")
            sys.exit(1)
        except Exception as err:
            if (
                "502: Bad Gateway" not in str(err)
                and "503: Service Unavailable" not in str(err)
                and "504: Gateway Timeout" not in str(err)
            ):
                print(traceback.format_exc(), f"[ERROR]: {err}")
                return err

            else:
                print(traceback.format_exc(), "[ERROR] - Retry")

            sys.exit(1)

    return _inner_function


@_generic_exception_handler
def config_parser() -> tuple[str, str, str, str, str]:
    """
    Parse the system for a config file OR environment variables for the script to use
    The default behavior is to try a config file first, and then defer to environment variables

    Returns:
        - WIZ_API_URL: the wiz api endpoint url pulled from the config file or the local environment variables
        - WIZ_CLIENT_ID: the wiz client id pulled from the config file or the local environment variables
        - WIZ_CLIENT_SECRET: the wiz client secret pulled from the config file or the local environment variables
        - WIZ_AUTH_URL: the wiz client id pulled from the config file or the local environment variables

    """

    WIZ_AUTH_ENDPOINTS = [
        "https://auth.app.wiz.io/oauth/token",  # Cognito
        "https://auth.wiz.io/oauth/token",  # Auth0 [legacy auth provider]
    ]
    wiz_api_url, wiz_client_id, wiz_client_secret, wiz_auth_url= "", "", "", ""
    try:
        with open(f"{wiz_config_file}", mode="r") as config_file:
            config = json.load(config_file)
            wiz_api_url = str(config["wiz_api_url"])
            wiz_client_id = str(config["wiz_client_id"])
            wiz_client_secret = str(config["wiz_client_secret"])
            wiz_auth_url = str(config["wiz_auth_url"])
           
            if not wiz_client_id or not wiz_client_secret:
                sys.exit(
                    f"Blank credentials. Please check your credentials and try again. Exiting..."
                )
    except FileNotFoundError:
        pass

    try:
        if os.getenv("wiz_client_id") or os.getenv("wiz_client_secret") or os.getenv("wiz_api_url"):
            wiz_client_id = os.getenv("wiz_client_id")
            wiz_client_secret = os.getenv("wiz_client_secret")
            wiz_api_url = os.getenv("wiz_api_url")
        if os.getenv("wiz_auth_url") in WIZ_AUTH_ENDPOINTS:
            wiz_auth_url = os.getenv("wiz_auth_url")

    except Exception:
        sys.exit(
            f"Unable to find one or more Wiz environment variables. Please check them and try again."
        )

    return (
        wiz_api_url,
        wiz_client_id,
        wiz_client_secret,
        wiz_auth_url
        
    )


############### End Helpers ###############

############### Start Script Config CONSTS ###############
SCRIPT_NAME = "Create Wiz Projects and assign subscriptions based on Tags"
SCRIPT_DESCRIPTION = """DESCRIPTION:\n  - This script will create new Wiz projects  based on  subscription Tags\n  - And also assign  subscriptions to Wiz projects based on Tags"""
(
    WIZ_API_URL,
    WIZ_CLIENT_ID,
    WIZ_CLIENT_SECRET,
    WIZ_AUTH_URL
) = config_parser()
# Standard headers
HEADERS_AUTH = {"Content-Type": "application/x-www-form-urlencoded"}
HEADERS = {"Content-Type": "application/json"}
############### End Script Config CONSTS ###############

############### Start functions ###############

@_generic_exception_handler
def request_wiz_api_token(auth_url: str, client_id: str, client_secret: str) -> None:
    """
    Request a token to be used to authenticate against the wiz API

    Parameters:
        - client_id: the wiz client ID
        - client_secret: the wiz secret

    Returns:
        - TOKEN: A session token
    """
    audience = (
        "wiz-api" if "auth.app" in auth_url or "auth.gov" in auth_url else "beyond-api"
    )

    auth_payload = {
        "grant_type": "client_credentials",
        "audience": audience,
        "client_id": client_id,
        "client_secret": client_secret,
    }

    # Request token from the Wiz API
    response = requests.post(
        url=auth_url, headers=HEADERS_AUTH, data=auth_payload, timeout=None
    )

    if response.status_code != requests.codes.ok:
        raise Exception(
            f"Error authenticating to Wiz {response.status_code} - {response.text}"
        )

    response_json = response.json()

    response.close()

    TOKEN = response_json.get("access_token")

    if not TOKEN:
        raise Exception(
            f'Could not retrieve token from Wiz: {response_json.get("message")}'
        )

    HEADERS["Authorization"] = "Bearer " + TOKEN


@_generic_exception_handler
def query_wiz_api(query: str, variables: dict, close_connection=False) -> str:
    """
    Query the WIZ API for the given query data schema
    Parameters:
        - query: the query or mutation we want to run
        - variables: the variables to be passed with the query or mutation
    Returns:
        - result: a json representation of the request object
    """

    data = {"variables": variables, "query": query}
    result = requests.post(url=WIZ_API_URL, json=data, headers=HEADERS)
    
    result_json = result.json()
    if close_connection:
        result.close()

    if (
        "access denied, at least one of the following is required"
        in result_json.values()
    ):
        raise Exception(f'Please check your permissions: {result_json["message"]}')
    else:
        return result_json

@_generic_exception_handler
def get_subs_with_tag_key ()-> list:
    """
    A wrapper around the query_wiz_api function
    That gets all the subscrictions that are tagged with tag_key
    Returns:
        - subs_nodes: Subsbscriptions tagged with tag_key
    """
    subs_query = """
        query GraphSearch(
            $query: GraphEntityQueryInput
            $controlId: ID
            $projectId: String!
            $first: Int
            $after: String
            $fetchTotalCount: Boolean!
            $quick: Boolean
        ) {
            graphSearch(
            query: $query
            controlId: $controlId
            projectId: $projectId
            first: $first
            after: $after
            quick: $quick
            ) {
            totalCount @include(if: $fetchTotalCount)
            maxCountReached @include(if: $fetchTotalCount)
            pageInfo {
                endCursor
                hasNextPage
            }
            nodes {
                entities {
                id
                name
                type
                properties
                originalObject
                }
            }
            }
        }
    """

    subs_variables = {
                "first": 100,
                "query": {
                    "type": [
                        "SUBSCRIPTION"
                    ],
                    "select": True,
                    "where": {
                        "tags": {
                            "TAG_CONTAINS_ALL": [
                            {
                                "key": tag_key
                            }
                            ]
                        }
                    }
                },
                "projectId": "*",
                "fetchTotalCount": True,
                "quick": False
                    
                }

    # Query the wiz API
    result = query_wiz_api(
        query=subs_query,
        variables=subs_variables,
    )
    print("Getting Subscriptions list")
    # Get the data back from each page
    # and append to our dictionary
    subs_nodes = result['data']['graphSearch']['nodes']

    # Use the page_info to query all pages
    page_info = result['data']['graphSearch']['pageInfo']

    # Count starting at 1 because we always sent at least 1 page
    page_count = 1
    
    # Continue querying until we have no pages left
    while page_info["hasNextPage"]:
        # Increment page count with each page
        page_count += 1

        # Advance the cursor
        print("There is more subscription to fetch, getting more data... (paginating)")
        subs_variables['after'] = result['data']['graphSearch']['pageInfo']['endCursor']

        # Query the API, now with a new after value
        result = query_wiz_api(
            query=subs_query,
            variables=subs_variables,
        )

        # Get the data back from each page
        # Each data item is a list of dicts, so append to the list
        # Giving us a list-of-lists-of dicts
        subs_nodes +=(result['data']['graphSearch']['nodes'])
        page_info = result['data']['graphSearch']['pageInfo']

    result = query_wiz_api(query="", variables={"": ""}, close_connection=True)

    return subs_nodes


@_generic_exception_handler
def get_all_wiz_projects()-> list:
    """
    A wrapper around the query_wiz_api function
    That gets all the Wiz projects
    Returns:
        - project_nodes: All wiz projects
    """
    allProjects_query = """
        query GraphSearch(
            $query: GraphEntityQueryInput
            $controlId: ID
            $projectId: String!
            $first: Int
            $after: String
            $fetchTotalCount: Boolean!
            $quick: Boolean
        ) {
            graphSearch(
            query: $query
            controlId: $controlId
            projectId: $projectId
            first: $first
            after: $after
            quick: $quick
            ) {
            totalCount @include(if: $fetchTotalCount)
            maxCountReached @include(if: $fetchTotalCount)
            pageInfo {
                endCursor
                hasNextPage
            }
            nodes {
                entities {
                id
                name
                }
            }
            }
        }
    """

    allProjects_variables = {
                "first": 100,
                "query": {
                    "type": [
                        "PROJECT"
                    ],
                    "select": True
                },
                "projectId": "*",
                "fetchTotalCount": True,
                "quick": False
                    
                }
    # Query the wiz API
    result = query_wiz_api(
        query=allProjects_query,
        variables=allProjects_variables,
    )
    print("Getting Projects list")
    # Get the data back from each page
    # and append to our dictionary
    projects_nodes = result['data']['graphSearch']['nodes']

    # Use the page_info to query all pages
    page_info = result['data']['graphSearch']['pageInfo']

    # Count starting at 1 because we always sent at least 1 page
    page_count = 1
    
    # Continue querying until we have no pages left
    while page_info["hasNextPage"]:
        # Increment page count with each page
        page_count += 1

        # Advance the cursor
        print("There is more project to fetch, getting more data... (paginating)")
        allProjects_variables['after'] = result['data']['graphSearch']['pageInfo']['endCursor']

        # Query the API, now with a new after value
        result = query_wiz_api(
            query=allProjects_query,
            variables=allProjects_variables,
        )

        # Get the data back from each page
        # Each data item is a list of dicts, so append to the list
        # Giving us a list-of-lists-of dicts
        projects_nodes +=result['data']['graphSearch']['nodes']
        page_info = result['data']['graphSearch']['pageInfo']

    result = query_wiz_api(query="", variables={"": ""}, close_connection=True)

    return projects_nodes


@_generic_exception_handler
def get_project_based_name(project_name:str)-> str:
    """
    A wrapper around the query_wiz_api function
    That gets info about a Wiz project
    Parameters:
        - project_name: the name of the project we want to get details for
    Returns:
        - project_data: information about the project
    """

    getProjects_query = """
        query ProjectsTable(
            $filterBy: ProjectFilters
            $first: Int
            $after: String
            $orderBy: ProjectOrder
        ) {
            projects(
            filterBy: $filterBy
            first: $first
            after: $after
            orderBy: $orderBy
            ) {
            nodes {
                id
                name
                cloudAccountLinks {
                    cloudAccount {
                    id
                    }
                    environment
                    shared
                }
            }
            pageInfo {
                hasNextPage
                endCursor
            }
            totalCount
            }
        }
        """
    getProjects_variables = {
        "first": 500,
        "filterBy": {
            "search": project_name
        },
        "orderBy": {
            "field": "SECURITY_SCORE",
            "direction": "ASC"
        }
    }
    result = query_wiz_api(
        query=getProjects_query,
        variables=getProjects_variables,
    )

    projects_with_name_in_them = result['data']['projects']['nodes']
    exact_match_projects  = []
    for p in projects_with_name_in_them:
        if p['name'] == project_name:
            exact_match_projects.append(p)

    return exact_match_projects



@_generic_exception_handler
@dryable.Dryable() 
def create_project(project_name:str)-> None:
    """
    A wrapper around the query_wiz_api function
    That creates a new wiz project
    Parameters:
        - project_name: the name of the project we want to create
    Returns:
        - none
    """

    createProject_query = """
        mutation CreateProject($input: CreateProjectInput!) {
        createProject(input: $input) {
            project {
            id
            }
        }
        }
    """

    createProject_variables = {
        "input": {
            "name": project_name,
            "identifiers": [],
            "cloudOrganizationLinks": [],
            "repositoryLinks": [],
            "description": "",
            "securityChampions": [],
            "projectOwners": [],
            "businessUnit": "",
            "riskProfile": {
                "businessImpact": "MBI",
                "hasExposedAPI": "YES",
                "hasAuthentication": "UNKNOWN",
                "isCustomerFacing": "NO",
                "isInternetFacing": "YES",
                "isRegulated": "YES",
                "sensitiveDataTypes": [],
                "storesData": "YES",
                "regulatoryStandards": []
            }
        }
    }
    result = query_wiz_api(
        query=createProject_query,
        variables=createProject_variables,
    )
    query_wiz_api(query="", variables={"": ""}, close_connection=True)

    if "errors" in result:
        print(f'\n└─ Cannot Create Project "{project_name}" because :')
        print (result['errors'][0]['message'])
        raise Exception
    else:
        print(f'\n└─ DONE: Created Project "{project_name}".')
        print(
            "\n└── Consider editing the newly created project and tweaking its settings."
            "\n└── e.g., description, risk profiile, regulatory standards, etc.",
        )



@_generic_exception_handler
@dryable.Dryable() 
def add_sub_to_project(project_id:str, cloudAccounts_list:list)-> None:
    """
    A wrapper around the query_wiz_api function
    That adds subscriptions to a project
    Parameters:
        - project_id: the UID of the project we want to add subscriptions to
        - cloud_accounts: the UIDs of the clound accounts/subscriptions we want to add to the project
    Returns:
        - none
    """

    addSubToProject_query = """
    mutation UpdateProject($input: UpdateProjectInput!) {
        updateProject(input: $input) {
            project {
            id
            }
        }
        }
    """

    addSubToProject_variables = {
        'input': {
            'id': project_id,
            'patch': {
                'cloudAccountLinks': cloudAccounts_list
            }
        }
    }

    result = query_wiz_api(
        query=addSubToProject_query,
        variables=addSubToProject_variables,
    )
    query_wiz_api(query="", variables={"": ""}, close_connection=True)

@_generic_exception_handler

def if_project_exist(project_nodes:list,project_name:str)-> bool:
    """
    A function that checks if there is a project with name project_name
    Parameters:
        - project_nodes: A List of Wiz projects
    Returns:
        - exist : boolean. True if a project with name project_name exist and False if it doesn't exist
    """
    exist = False
    for project in project_nodes:
        if project_name == project['entities'][0]['name']:
            exist = True
            return exist
    return exist


@_generic_exception_handler
def get_subs_tag_value(subs_nodes:list)-> list:
    """
    Processes the list of subscriptions
    Parameters:
        - subs_nodes: A List of Wiz subscriptions
    Returns:
        - subs_list : list of subscriptions. Each subscription is a dictionary of name, id and tag_key
        - tag_value_list : The tag value of tagged subscriptions with tag_key
    """
    subs_list = []
    tag_value_list =[]
    for sub in subs_nodes:
        subs_tags = {'name': sub['entities'][0]['name'],'id': sub['entities'][0]['id'],
            tag_key: sub['entities'][0]['properties']['tags'][tag_key]}
        tag_value_list.append (sub['entities'][0]['properties']['tags'][tag_key])
        subs_list.append (subs_tags)
    return subs_list,list(set(tag_value_list))

############### End functions ###############




############### Init main, call functions, helpers ###############
def main():
    print_logo()

    # request_wiz_api_token(client_id=client_id, client_secret=client_secret)
    request_wiz_api_token(
        auth_url=WIZ_AUTH_URL, client_id=WIZ_CLIENT_ID, client_secret=WIZ_CLIENT_SECRET
    )
    # Get the list of subscriptions tagged with tag_key
    subs_nodes = get_subs_with_tag_key()
    # Get the list of all Wiz Projects
    project_nodes = get_all_wiz_projects()

    # Go over the values of tag_key and check if there is a corresponding project
    # Create a new project with name project_name_prefix +tag_value if it doesn't exist
    for tag_value in get_subs_tag_value(subs_nodes)[1]:
        project_name= project_name_prefix +tag_value
        if if_project_exist(project_nodes,project_name):
            print ("Project "+project_name+" exist")
        else:
            print ("Creating project "+project_name)
            create_project(project_name)

    # Go over the subscriptons tagged with tag_key and add them to the project with name project_name_prefix +tag_value
    # The script will keep any existing subscription associated with project_name. It will only add new subscriptions to it and doesn't wipe existing ones

    for sub in get_subs_tag_value(subs_nodes)[0]:
        project_name = project_name_prefix +sub[tag_key]
        project = get_project_based_name(project_name)
        print 
        if len(project) == 0 and '--dry-run' in sys.argv and 'yes' in sys.argv:
            print ("adding subscription "+sub['name']+" to project "+project_name)
        else:
            cloudAccounts_list= [{'cloudAccount': link['cloudAccount']['id'],'environment':link['environment'],'shared':link['shared']}   for link in project[0]['cloudAccountLinks']]   
            if sub ['id'] in [cloudAccount['cloudAccount'] for cloudAccount in cloudAccounts_list]:
                print ("Subscription "+sub['name']+" is already assigned to project "+project_name)
            else:
                cloudAccounts_list.append({'cloudAccount': sub['id'],'environment': 'PRODUCTION','shared': False})
                print ("adding subscription "+sub['name']+" to project "+project_name)
                add_sub_to_project(project[0]['id'], cloudAccounts_list)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n└─ Ctrl+C interrupt received. Exiting.")
        pass