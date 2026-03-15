"""Background worker entrypoint for async optimization jobs."""

import json;
import os;
import traceback;

import from interfaces.cli.cli { run_optimization_request }


def _load_request -> dict {
    request_file = os.environ.get("RINGTAIL_ASYNC_REQUEST_FILE", "");
    if request_file == "" {
        raise ValueError("RINGTAIL_ASYNC_REQUEST_FILE is required");
    }
    with open(request_file, "r") as f {
        return json.loads(f.read());
    }
}


with entry {
    try {
        request = _load_request();
        result = run_optimization_request(request);
        print(json.dumps(result));
    } except Exception as e {
        failure = {
            "error": "Async worker failed: " + str(e),
            "traceback": traceback.format_exc()
        };
        print(json.dumps(failure));
        raise e;
    }
}
