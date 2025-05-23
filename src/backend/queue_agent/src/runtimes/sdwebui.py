# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import base64
import json
import logging
import time
import traceback

from requests.exceptions import ReadTimeout, HTTPError
from modules import http_action, misc

logger = logging.getLogger("queue-agent")

ALWAYSON_SCRIPTS_EXCLUDE_KEYS = ['task', 'id_task', 'uid',
                                 'sd_model_checkpoint', 'image_link', 'save_dir', 'sd_vae', 'override_settings']

# Import the safe_xray_capture decorator from main module
try:
    from src.main import safe_xray_capture, xray_enabled
except ImportError:
    try:
        # Try alternative import path
        from ..main import safe_xray_capture, xray_enabled
    except ImportError:
        # Fallback if import fails - create a simple pass-through decorator
        logger.warning("Failed to import safe_xray_capture from main, using fallback")
        def safe_xray_capture(name):
            def decorator(func):
                return func
            return decorator
        xray_enabled = False

def check_readiness(api_base_url: str, dynamic_sd_model: bool) -> bool:
    """Check if SD Web UI is ready by invoking /option endpoint"""
    while True:
        try:
            logger.info('Checking service readiness...')
            # checking with options "sd_model_checkpoint" also for caching current model
            opts = invoke_get_options(api_base_url)
            logger.info('Service is ready.')
            if "sd_model_checkpoint" in opts:
                if opts['sd_model_checkpoint'] != None:
                    current_model_name = opts['sd_model_checkpoint']
                    logger.info(f'Init model is: {current_model_name}.')
                else:
                    if dynamic_sd_model:
                        logger.info(f'Dynamic SD model is enabled, init model is not loaded.')
                    else:
                        logger.error(f'Init model {current_model_name} failed to load.')
            break
        except Exception as e:
            logger.debug(repr(e))
            time.sleep(1)
    return True

def handler(api_base_url: str, task_type: str, task_id: str, payload: dict, dynamic_sd_model: bool) -> dict:
    """Main handler for SD Web UI request"""
    response = {}
    try:
        logger.info(f"Start process {task_type} task with ID: {task_id}")
        match task_type:
            case 'text-to-image':
                # Compatiability for v1alpha1: Ensure there is an alwayson_scripts
                if 'alwayson_scripts' in payload:
                    # Switch model if necessery
                    if dynamic_sd_model and payload['alwayson_scripts']['sd_model_checkpoint']:
                        new_model = payload['alwayson_scripts']['sd_model_checkpoint']
                        logger.info(f'Try to switching model to: {new_model}.')
                        current_model_name = switch_model(api_base_url, new_model)
                        if current_model_name is None:
                            raise Exception(f'Failed to switch model to {new_model}')
                        logger.info(f'Current model is: {current_model_name}.')
                else:
                    payload.update({'alwayson_scripts': {}})

                task_response = invoke_txt2img(api_base_url, payload)

            case 'image-to-image':
                # Compatiability for v1alpha1: Ensure there is an alwayson_scripts
                if 'alwayson_scripts' in payload:
                    # Switch model if necessery
                    if dynamic_sd_model and payload['alwayson_scripts']['sd_model_checkpoint']:
                        new_model = payload['alwayson_scripts']['sd_model_checkpoint']
                        logger.info(f'Try to switching model to: {new_model}.')
                        current_model_name = switch_model(api_base_url, new_model)
                        if current_model_name is None:
                            raise Exception(f'Failed to switch model to {new_model}')
                        logger.info(f'Current model is: {current_model_name}.')
                else:
                    payload.update({'alwayson_scripts': {}})

                task_response = invoke_img2img(api_base_url, payload)
            case 'extra-single-image':
                # There is no alwayson_script in API spec
                task_response = invoke_extra_single_image(api_base_url, payload)
            case 'extra-batch-image':
                task_response = invoke_extra_batch_images(api_base_url, payload)
            case _:
                # Catch all
                logger.error(f'Unsupported task type: {task_type}, ignoring')

        imgOutputs = post_invocations(task_response)
        logger.info(f"Received {len(imgOutputs)} images")
        content = json.dumps(succeed(task_id, task_response))
        response["success"] = True
        response["image"] = imgOutputs
        response["content"] = content
        logger.info(f"End process {task_type} task with ID: {task_id}")
    except ReadTimeout as e:
        invoke_interrupt(api_base_url)
        content = json.dumps(failed(task_id, e))
        logger.error(f"{task_type} task with ID: {task_id} timeouted")
        traceback.print_exc()
        response["success"] = False
        response["content"] = content
    except Exception as e:
        content = json.dumps(failed(task_id, e))
        logger.error(f"{task_type} task with ID: {task_id} finished with error")
        traceback.print_exc()
        response["success"] = False
        response["content"] = content
    return response

@safe_xray_capture('text-to-image')
def invoke_txt2img(api_base_url: str, body) -> str:
    # Compatiability for v1alpha1: Move override_settings from header to body
    override_settings = {}
    if 'override_settings' in body['alwayson_scripts']:
        override_settings.update(body['alwayson_scripts']['override_settings'])
    if override_settings:
        if 'override_settings' in body:
            body['override_settings'].update(override_settings)
        else:
            body.update({'override_settings': override_settings})

    # Compatiability for v1alpha1: Remove header used for routing in v1alpha1 API request
    body.update({'alwayson_scripts': misc.exclude_keys(body['alwayson_scripts'], ALWAYSON_SCRIPTS_EXCLUDE_KEYS)})

    # Process image link in elsewhere in body
    body = download_image(body)

    response = http_action.do_invocations(api_base_url+"txt2img", body)
    return response

@safe_xray_capture('image-to-image')
def invoke_img2img(api_base_url: str, body: dict) -> str:
    """Image-to-Image request"""
    # Process image link
    body = download_image(body)

    # Compatiability for v1alpha1: Move override_settings from header to body
    override_settings = {}
    if 'override_settings' in body['alwayson_scripts']:
        override_settings.update(body['alwayson_scripts']['override_settings'])
    if override_settings:
        if 'override_settings' in body:
            body['override_settings'].update(override_settings)
        else:
            body.update({'override_settings': override_settings})

    # Compatiability for v1alpha2: Process image link in "Alwayson_scripts"
    # Plan to remove in next release
    if 'image_link' in body['alwayson_scripts']:
        body.update({"init_images": [body['alwayson_scripts']['image_link']]})

    # Compatiability for v1alpha1: Remove header used for routing in v1alpha1 API request
    body.update({'alwayson_scripts': misc.exclude_keys(body['alwayson_scripts'], ALWAYSON_SCRIPTS_EXCLUDE_KEYS)})

    response = http_action.do_invocations(api_base_url+"img2img", body)
    return response

@safe_xray_capture('extra-single-image')
def invoke_extra_single_image(api_base_url: str, body) -> str:
    body = download_image(body)
    response = http_action.do_invocations(api_base_url+"extra-single-image", body)
    return response

@safe_xray_capture('extra-batch-images')
def invoke_extra_batch_images(api_base_url: str, body) -> str:
    body = download_image(body)
    response = http_action.do_invocations(api_base_url+"extra-batch-images", body)
    return response

def invoke_set_options(api_base_url: str, options: dict) -> str:
    return http_action.do_invocations(api_base_url+"options", options)

def invoke_get_options(api_base_url: str) -> str:
    return http_action.do_invocations(api_base_url+"options")

def invoke_get_model_names(api_base_url: str) -> str:
    return sorted([x["title"] for x in http_action.do_invocations(api_base_url+"sd-models")])

def invoke_refresh_checkpoints(api_base_url: str) -> str:
    return http_action.do_invocations(api_base_url+"refresh-checkpoints", {})

def invoke_unload_checkpoints(api_base_url: str) -> str:
    return http_action.do_invocations(api_base_url+"unload-checkpoint", {})

def invoke_interrupt(api_base_url: str) -> str:
    return http_action.do_invocations(api_base_url+"interrupt", {})

def switch_model(api_base_url: str, name: str) -> str:
    opts = invoke_get_options(api_base_url)
    current_model_name = opts['sd_model_checkpoint']

    if current_model_name == name:
        logger.info(f"Model {current_model_name} is currently loaded, ignore switch.")
    else:
        # refresh then check from model list
        invoke_refresh_checkpoints(api_base_url)
        models = invoke_get_model_names(api_base_url)
        if name in models:
            if (current_model_name != None):
                logger.info(f"Model {current_model_name} is currently loaded, unloading... ")
                try:
                    invoke_unload_checkpoints(api_base_url)
                except HTTPError:
                    logger.info(f"No model is currently loaded. Loading new model... ")
            options = {}
            options["sd_model_checkpoint"] = name
            invoke_set_options(api_base_url, options)
            current_model_name = name
        else:
            logger.error(f"Model {name} not found, keeping current model.")
            return None

    return current_model_name

# Customizable for success responses
def succeed(task_id, response):
    parameters = {}
    if 'parameters' in response: # text-to-image and image-to-image
        parameters = response['parameters']
        parameters['id_task'] = task_id
        parameters['image_seed'] = ','.join(
            str(x) for x in json.loads(response['info'])['all_seeds'])
        parameters['error_msg'] = ''
    elif 'html_info' in response: # extra-single-image and extra-batch-images
        parameters['html_info'] = response['html_info']
        parameters['id_task'] = task_id
        parameters['error_msg'] = ''
    return {
        'images': [''],
        'parameters': parameters,
        'info': ''
    }


# Customizable for failure responses
def failed(task_id, exception):
    parameters = {}
    parameters['id_task'] = task_id
    parameters['status'] = 0
    parameters['error_msg'] = repr(exception)
    parameters['reason'] = exception.response.json() if hasattr(exception, "response") else None
    return {
        'images': [''],
        'parameters': parameters,
        'info': ''
    }

def download_image(obj, path=""):
    """Search URL in object, and replace all URL with content of URL"""
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            obj[key] = download_image(value, new_path)
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            new_path = f"{path}[{index}]"
            obj[index] = download_image(item, new_path)
    elif isinstance(obj, str):
        if (obj.startswith('http') or obj.startswith('s3://')):
            logger.info(f"Found URL {obj} in {path}, replacing... ")
            try:
                image_byte = misc.encode_to_base64(http_action.get(obj))
                logger.info(f"Replaced {path} with content")
            except Exception as e:
                logger.error(f"Error fetching URL: {obj}")
                logger.error(f"Error: {str(e)}")
            return image_byte
    return obj

def post_invocations(response):
    img_bytes = []

    if "images" in response.keys():
        for i in response["images"]:
            img_bytes.append(base64.b64decode(i))

    elif "image" in response.keys():
        img_bytes.append(base64.b64decode(response["image"]))

    return img_bytes