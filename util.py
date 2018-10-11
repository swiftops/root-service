import requests
from database_util import get_master_collection, get_service_collection, get_account_history_collection
from authentication import validate_user
import json, re
from logger_util import get_logger
from datetime import datetime
from flask import jsonify
from elasticapm.contrib.flask import ElasticAPM
from consul_util import get_config_value

logger = get_logger()


def load_autocomplete_data(user_query, show_more):
    """this api is to autocomplete the user request based on
    the input entered in the search box from master collection"""
    try:
        db = get_master_collection()
        outer_list = []
        inner_list = []
        auto_list = []
        query = user_query.strip().lower()
        query_splitted = query.split()

        if "." in query:
            query = query_splitted[0].split(".")[1]

        if len(query_splitted) > 1:
            result = db.find({"master.key": {"$regex": query_splitted[0], "$options": "i"}})
        else:
            result = db.find({"master.key": {"$regex": query, "$options": "i"}})

        display_threshold = 500
        if show_more is None:
            display_threshold = 5

        for item in result:
            item_key = item["master"]["key"]
            item_value = item["master"]["value"]
            local_count = 1
            for e in sorted(item_value, reverse=True):
                if local_count <= display_threshold:
                    master_key = item_key
                    if item_key and isinstance(item_key, list):
                        for key in master_key:
                            if len(query_splitted) == 1:
                                if (key.find(query)) != -1:
                                    master_key = str(key)
                                    break
                            elif len(query_splitted) > 1:
                                if (key.find(query_splitted[0])) != -1:
                                    master_key = str(key)
                                    break
                            elif (query.find(key)) != -1:
                                master_key = str(key)
                                break

                    rel_str = master_key + " " + str(e).lower()
                    if query in rel_str:
                        outer_list.append(master_key + " " + e)
                        list_value = item_value[e]
                        inner_list.append(_natural_sort(list_value))
                    local_count = int(local_count) + 1
                else:
                    break

            auto_list.append(item_key)
            auto_list.append(outer_list)
            auto_list.append(inner_list)
    except Exception as e:
        logger.error("Exception in  _load_autocomplete_data : " + str(e))
        data = {}
        out_list = []
        data["format"] = "error" + str(e)
        in_list = [data]
        auto_list = [out_list, in_list]
    return auto_list


def filter_request(query, username, firstreq):
    """this api is to identify the user request and forward the request to filter, read the response data
    and forward it to search box"""
    try:
        keyword = query.split(";")[0].split(" ")[0]
        validate_user(username)
        if _show_all_report(keyword):
            query = query.split("~")[0]
            data = _init_report_load(query)
        else:
            filter_url = _fetch_service_filter_url(keyword)
            if "dashboard_url" == filter_url["format"]:
                data = dashboard_url(filter_url["service_url"], query)
                data["format"] = "url"
            else:
                query = query.split("~")[0]
                if len(filter_url['url'].strip()) > 0:
                    data = _call_rest_api(filter_url["url"], query, 'post')
                else:
                    data = _create_rest_error_output("No Such element", 500)
                data["format"] = filter_url["format"]
            out_list = [filter_url["label"]]
            in_list = [data]
            response_list = [out_list, in_list]
            data = response_list
    except Exception as e:
        logger.error("Exception in _filter_request : " + str(e))
        data = {"success": "", "data": {}, "error": {"Message": str(e)}}
        data = jsonify(data)
    return data


def _call_rest_api(url, input_data, request_type):
    """Calls the other rest api's"""
    try:
        if request_type == 'post':
            req = requests.post(url, params=input_data, json=input_data, timeout=30)
        else:
            req = requests.get(url, params=input_data, timeout=30)
        response = req.text
        val = json.loads(response)
    except Exception as e:
        logger.error("Exception in _call_rest_api : " + str(e))
        raise ValueError("Filter is down!!!!")
    return val


def add_data_in_session(session, user_query, session_id, data_type, add_if_exist):
    """Adds the user queries in the session"""
    query_list = []
    session_list = session.get(session_id)
    flag = False
    if session_list is None:
        session[session_id] = [{data_type: user_query}]
    elif session_list is not None and add_if_exist:
        for item in session_list:
            if data_type in item:
                item[data_type] += [user_query.strip()]
                flag = True
                break
        if not flag:
            session[session_id] = session_list + [{data_type: [user_query]}]
    else:
        if add_if_exist:
            query_list.append(user_query.strip())
            session[session_id] = session_list + [{data_type: [query_list]}]
    return None


def _find_filter(keyword):
    """finds the filter url from services collection"""
    db = get_service_collection()
    result = db.find({"name": {"$regex": keyword}})
    service_endpoint = ''
    for item in result:
        service_endpoint = item["value"]["url"]
    return service_endpoint


def _init_report_load(input_data):
    """Gets the first 5 services and get its response, append it and return to conversational ui"""
    report_keys = []
    report_list = []
    reports = []
    db = get_service_collection()

    services = db.find({}).limit(10)
    for service in services:
        try:
            is_enable = service["value"]["enable"]
            if is_enable is not None and "Y" in is_enable:
                try:
                    if "dashboard_url" == service["value"]["format"]:
                        data = dashboard_url(service["value"]["url"]["service_url"], input_data)
                        data["format"] = "url"
                    else:
                        data = _call_rest_api(str(_fetch_service_filter_url(service["name"])["url"]), input_data + ";" + service["name"], 'post')
                        data["format"] = service["value"]["format"]
                    report_keys.append(service["value"]["label"])
                    report_list.append(data)
                except Exception as e:
                    logger.error("Exception in : " + service["name"] + str(e))
        except Exception as e:
            logger.error("Exception in _init_report_load : " + str(e))
            raise ValueError(e)
    reports.append(report_keys)
    reports.append(report_list)
    return reports


def _fetch_service_filter_url(name):
    """Fetches service url from mongo db"""
    db = get_service_collection()
    result = db.find({"name": {"$regex": name.strip(), "$options": "i"}})
    filter_url = {}
    for url in result:
        filter_url["url"] = url["value"]["filter_url"]
        filter_url["format"] = url["value"]["format"]
        filter_url["label"] = url["value"]["label"]
        try:
            filter_url["service_url"] = url["value"]["url"]["service_url"]
        except Exception as e:
            print("")
        break
    return filter_url


def _create_rest_error_output(error_message, error_code):
    """creates rest service error output"""
    response = {
        "success": "false",
        "data": {},
        "error": {
            "code": error_code,
            "message": error_message
        }
    }
    return response


def _natural_sort(alphanumeric_data):
    """Alphanumeric sorting in reverse order to get latest release and build"""
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(alphanumeric_data, key=alphanum_key, reverse=True)


def _show_all_report(keyword):
    show_all_flag = True
    show_all = None
    db = get_service_collection()
    result = db.find({"name": {"$regex": keyword.strip(), "$options": "i"}})
    for item in result:
        show_all = item["value"]["show_all"]
    if show_all == 'N':
        show_all_flag = False
    return show_all_flag


def _insert_account_history(input_json):
    db = get_account_history_collection()
    try:
        result = db.insert_one(input_json)
        data = {
            "result id": str(result.inserted_id)
        }
        response = _create_rest_success_output(data)
    except Exception as e:
        response = _create_rest_error_output("Error while registering service : " + str(e), 500)
    return response


def _create_rest_success_output(data):
    response = {
        "success": "true",
        "data": data,
        "error": {}
    }
    return response


def insert_on_logout(session, session_list, username, session_id):
    user_query = ''
    login_time = ''
    if session is not None and session_list is not None:
        for item in session_list:
            if "query" in item:
                user_query = item["query"]
            if "login_time" in item:
                login_time = item["login_time"]

    input_data = {
        "user_id": username,
        "session_id": session_id,
        "query": user_query,
        "login_time": login_time,
        "logout_time": str(datetime.now())
    }
    response = _insert_account_history(input_data)
    return response


def init(app):
    apm = None
    if get_config_value('ENABLE_APM') is not None and 'Y' in str(get_config_value('ENABLE_APM')):
        app.config['ELASTIC_APM'] = {
            'SERVICE_NAME': 'rootservice',
            'SERVER_URL': get_config_value('APM_SERVER_URL').decode(encoding="utf-8"),
            'DEBUG': True
        }
        apm = ElasticAPM(app)
    return apm


def dashboard_url(url, input_data):
    ''' This api replaces the placeholders with the selected values in the url'''
    input_val = input_data.split(";")
    release = str(input_val[0].split(" ")[1]).replace("_", ".").strip()
    temp = input_val[1].strip()
    build = temp.split("~")[0].strip()
    if "#RELEASE#" in url:
        url = url.replace("#RELEASE#", release)
    if "#BUILD#" in url:
        url = url.replace("#BUILD#", build)
    if "#SCRIPT#" in url:
        user_text = input_data.split("~")[1]
        url = url.replace("#SCRIPT#", user_text)
    data = {"data": {"url": url}}
    return data

