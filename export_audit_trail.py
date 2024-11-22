import argparse
import csv
from datetime import datetime, timezone
import os
import requests
import sys

#################### AUXILIARY VARIABLES ####################

ENV_FILE = ".env"
HOSTNAME_ENV = "DOMINO_HOSTNAME"
JWT_ENV = "JWT"
API_KEY_ENV = "API_KEY"

AUDIT_TRAIL_PATH = "api/audittrail/v1/auditevents"
BATCH_LIMIT = 1000

CSV_BASE_FILENAME=f"audit_trail_export_{datetime.now().strftime('%Y-%m-%d:%H-%M-%S')}.csv"

# HEADERS
UTC_TIMESTAMP = "DATE & TIME (UTC)"
USER_NAME = "USER NAME"
EVENT = "EVENT"
TARGET_NAME = "TARGET NAME"
PROJECT_NAME = "PROJECT NAME"
DATASET_NAME = "DATASET NAME"
FILE_NAME = "FILE NAME"
TARGET_USER = "TARGET USER"
FEATURE_FLAG = "FEATURE FLAG"
OLD_VALUE = "OLD VALUE"
NEW_VALUE = "NEW VALUE"
ADDED_VALUE = "ADDED"
REMOVED_VALUE = "REMOVED"
JOBS = "JOBS"
COMMAND = "COMMAND"

CSV_HEADERS = [
    UTC_TIMESTAMP,
    USER_NAME,
    EVENT,
    TARGET_NAME,
    PROJECT_NAME,
    DATASET_NAME,
    FILE_NAME,
    TARGET_USER,
    FEATURE_FLAG,
    OLD_VALUE,
    NEW_VALUE,
    ADDED_VALUE,
    REMOVED_VALUE,
    JOBS,
    COMMAND,
]
#############################################################


def main():
    # Load any environment variables defined
    load_env_file()

    parser = argparse.ArgumentParser(description="Script that exports Audit trail events")

    parser.add_argument('--hostname',
                        help="Hostname. Can be defined in an .env file as HOSTNAME=your-hostname",
                        default=os.environ.get(HOSTNAME_ENV))
    parser.add_argument('--jwt',
                        help="JWT token. Can be defined in an .env file as JWT=your-jwt",
                        default=os.environ.get(JWT_ENV))
    parser.add_argument('--api-key',
                        help="API-Key. Can be defined in an .env file as API_KEY=your-api-key",
                        default=os.environ.get(API_KEY_ENV))

    # Arguments for the filters
    parser.add_argument('--event', help="Event name")
    parser.add_argument('--user_name', dest='actorName', help="User name that performed the action")
    parser.add_argument('--target_name', dest='targetName', help="Object that received the action")
    parser.add_argument('--project_name', dest='withinProjectName', help="Name of the project")
    parser.add_argument('--start_date', dest='startTimestamp', help="Timestamp from when to start looking data. Format: YYYY-MM-DD HH:MM:SS")
    parser.add_argument('--end_date', dest='endTimestamp', help="Timestamp up to when to look for data. Format: YYYY-MM-DD HH:MM:SS")

    args = parser.parse_args()

    print("Exporting Audit trail events using the following arguments:")
    print(f"- Hostname: {args.hostname}")
    print(f"- JWT: {'*****' if args.jwt else '-'}")
    print(f"- API Key: {'*****' if args.api_key else '-'}")
    print(f"- Start Date & Time: {args.startTimestamp or '-'}")
    print(f"- End Date & Time: {args.endTimestamp or '-'}")
    print(f"- Event: {args.event or '-'}")
    print(f"- User Name: {args.actorName or '-'}")
    print(f"- Target Name: {args.targetName or '-'}")
    print(f"- Project Name: {args.withinProjectName or '-'}")

    # Validations and clean-up
    if not args.hostname:
        print("Error: You must provide the hostname.")
        sys.exit(1)

    # Ensure either jwt or api-key is provided
    if not args.jwt and not args.api_key:
        print("Error: You must provide either a JWT token or an API key.")
        sys.exit(1)

    # Ensure no trailing / are added in the hostname
    if args.hostname.endswith('/'):
        args.hostname = args.hostname[:-1]

    # Ensure start and/or end timestamps have the right data and format them
    args.startTimestamp = validate_and_format_timestamp(args.startTimestamp) if args.startTimestamp else None
    args.endTimestamp = validate_and_format_timestamp(args.endTimestamp) if args.endTimestamp else None

    # args.startTimestamp = 1729185360064
    # args.endTimestamp = 1729185480361

    request_headers = build_request_headers(args.jwt, args.api_key)
    request_params = build_request_params(args)

    # Run the export
    export_audit_trail(args.hostname, request_headers, request_params)


def load_env_file():
    try:
        with open(ENV_FILE) as f:
            # Use a generator to process lines and filter comments and empty lines
            env_vars = (line.strip().split('=', 1) for line in f if line.strip() and not line.startswith('#'))
            # Set environment variables
            for key, value in env_vars:
                os.environ[key] = value
    except FileNotFoundError:
        print(f"No {ENV_FILE} file found. Skipping loading environment variables")


def validate_and_format_timestamp(raw_timestamp):
    try:
        parsed_start_timestamp = datetime.strptime(raw_timestamp, "%Y-%m-%d %H:%M:%S")
        # parsed_start_timestamp = parsed_start_timestamp.replace(tzinfo=timezone.utc)
        # Convert to Unix time (milliseconds) and return
        return int(parsed_start_timestamp.timestamp() * 1000)
    except ValueError:
        print(f"Error: Timestamp must be in the format 'YYYY-MM-DD HH:MM:SS'. Received: {raw_timestamp}")
        sys.exit(1)


def build_request_headers(jwt: str, api_key: str) -> dict:
    header = {"accept": "application/json"}
    if jwt:
        header['Authorization'] = f'Bearer {jwt}'
    else:
        header['X-Domino-Api-Key'] = api_key
    return header


def build_request_params(args: dict) -> dict:
    request_params = {key: value for key, value in vars(args).items() if value is not None and key not in ['hostname', 'jwt', 'api_key']}
    request_params["limit"] = BATCH_LIMIT
    request_params["sort"] = "-timestamp"
    return request_params


def export_audit_trail(hostname: str, request_headers: dict, request_params: dict) -> None:
    initialize_csv()

    offset = 0
    keep_extracting = True

    while keep_extracting:
        print(f'Obtaining new batch of events (Offset: {offset} | Limit {BATCH_LIMIT})')
        data = get_events_batch(hostname, request_headers, request_params, offset=offset)
        raw_events = data.get('events', [])

        parsed_events = parse_events(raw_events)

        write_to_csv(parsed_events)

        if len(raw_events) < BATCH_LIMIT:
            keep_extracting = False
        else:
            offset += BATCH_LIMIT


    print(f'Final offset: {offset}')
    print('Done!')


def initialize_csv():
    with open(CSV_BASE_FILENAME, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=CSV_HEADERS)
        writer.writeheader()


def get_events_batch(hostname, request_headers, request_params, offset=0):
    request_params["offset"] = offset

    audit_trail_path = f"{hostname}/{AUDIT_TRAIL_PATH}"

    response = requests.get(audit_trail_path, headers=request_headers, params=request_params)

    data = response.json()

    return data


def parse_events(raw_events):
    parsed_events = []
    for raw_event in raw_events:
        parsed_events.append(parse_event(raw_event))
    return parsed_events


def parse_event(raw_event):
    parsed_event = {
        UTC_TIMESTAMP: None,
        USER_NAME: None,
        EVENT: None,
        TARGET_NAME: None,
        PROJECT_NAME: None,
        DATASET_NAME: None,
        FILE_NAME: None,
        TARGET_USER: None,
        FEATURE_FLAG: None,
        JOBS: None,
        OLD_VALUE: None,
        NEW_VALUE: None,
        ADDED_VALUE: None,
        REMOVED_VALUE: None,
        COMMAND: None,
    }

    parsed_event[UTC_TIMESTAMP] = datetime.fromtimestamp(raw_event['timestamp'] / 1000, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    actor_data = raw_event.get('actor', {})
    parsed_event[USER_NAME] = actor_data.get('name', actor_data.get('id'))

    action_data = raw_event.get('action', {})
    parsed_event[EVENT] = action_data.get('eventName')

    in_data = raw_event.get('in', {})
    if in_data.get('entityType') == 'project':
        parsed_event[PROJECT_NAME] = in_data.get('name', in_data.get('id'))

    targets_raw = raw_event.get('targets', [])
    if targets_raw:
        target_data = flatten_target(targets_raw[0])

        parsed_event[TARGET_NAME] = target_data.get("name")
        parsed_event[OLD_VALUE] = target_data.get("before")
        parsed_event[NEW_VALUE] = target_data.get("after")
        parsed_event[ADDED_VALUE] = target_data.get("added")
        parsed_event[REMOVED_VALUE] = target_data.get("removed")

        if target_data["entityType"] == "user":
            parsed_event[TARGET_USER] = target_data.get("name")

        elif target_data["entityType"] in ("dataset", "datasetSnapshot"):
            parsed_event[DATASET_NAME] = target_data.get("name")

            if target_data.get("fieldName") == "filePath":
                parsed_event[FILE_NAME] = target_data.get("after")

        elif target_data["entityType"] in ("scheduledRun", "job"):
            parsed_event[JOBS] = target_data.get("name")
            parsed_event[COMMAND] = raw_event.get('metadata', {}).get('command')
            parsed_event[NEW_VALUE] = raw_event.get('metadata', {}).get('schedule') or parsed_event[NEW_VALUE]

        elif target_data["entityType"] == "featureFlag":
            parsed_event[FEATURE_FLAG] = target_data.get("name")

    affecting_raw = raw_event.get('affecting', [])
    if affecting_raw:
        for affecting in affecting_raw:
            if affecting.get("entityType") == "dataset":
                parsed_event[DATASET_NAME] = affecting.get("name", affecting.get("id"))
            elif affecting.get("entityType") in ("appliedUser", "user"):
                parsed_event[TARGET_USER] = affecting.get("name", affecting.get("id"))
            elif affecting.get("entityType") == "file":
                parsed_event[FILE_NAME] = affecting.get("name")

    parsed_event[COMMAND] = parsed_event[COMMAND] or raw_event.get('metadata', {}).get('query')

    return parsed_event


def flatten_target(target_raw):
    target_entity = target_raw.get("entity", {})
    target_data = {
        "entityType": target_entity.get("entityType"),
        "name": target_entity.get("name", target_entity.get("id")),
    }

    target_fields = target_raw.get("fieldChanges", [])
    if target_fields:
        target = target_fields[0]
        target_data["fieldName"] = target.get("fieldName")
        target_data["fieldType"] = target.get("fieldType")
        target_data["before"] = target.get("before")
        target_data["after"] = target.get("after")
        target_data["unit"] = target.get("unit")
        target_data["added"] = ','.join([obj.get("name") for obj in target.get("added", [])])
        target_data["removed"] = ','.join([obj.get("name") for obj in target.get("removed", [])])

    return target_data


def write_to_csv(parsed_events):
    with open(CSV_BASE_FILENAME, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=CSV_HEADERS)
        writer.writerows(parsed_events)


if __name__ == "__main__":
    main()
