import logging
import json
import uuid

class StructuredLogger:
    def __init__(self, name="search_engine"):
        self.logger = logging.getLogger(name)
        
        # Setup structured JSON formatter for ALL logs
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_obj = {
                    "level": record.levelname,
                    "logger": record.name
                }
                try:
                    msg_data = json.loads(record.getMessage())
                    log_obj.update(msg_data)
                except json.JSONDecodeError:
                    log_obj["msg"] = record.getMessage()
                if record.exc_info:
                    log_obj["exc_info"] = self.formatException(record.exc_info)
                return json.dumps(log_obj)

        root_logger = logging.getLogger()
        if not root_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(JSONFormatter())
            root_logger.addHandler(handler)
            root_logger.setLevel(logging.INFO)
            
        self.logger.setLevel(logging.INFO)

    def log_search(self, endpoint, query, timing, total_results, returned_results, mode=None, extra=None):
        log_data = {
            "event": "search_request",
            "request_id": str(uuid.uuid4()),
            "endpoint": endpoint,
            "mode": mode,
            "query_length": len(query) if query else 0,
            "total_results": total_results,
            "returned_results": returned_results,
            "timing_ms": {k: round(v * 1000, 2) for k, v in timing.items()},
        }
        if extra:
            log_data.update(extra)
            
        self.logger.info(json.dumps(log_data))

    def log_error(self, endpoint, error, mode=None):
        log_data = {
            "event": "search_error",
            "request_id": str(uuid.uuid4()),
            "endpoint": endpoint,
            "mode": mode,
            "error": str(error)
        }
        self.logger.error(json.dumps(log_data))

    def log_crawl(self, seed_url, stats, duration, error=None):
        log_data = {
            "event": "crawl_completed" if not error else "crawl_failed",
            "request_id": str(uuid.uuid4()),
            "seed_url": seed_url,
            "stats": stats,
            "duration_ms": round(duration * 1000, 2),
        }
        if error:
            log_data["error"] = str(error)
            self.logger.error(json.dumps(log_data))
        else:
            self.logger.info(json.dumps(log_data))

    def log_index(self, duration, stats, error=None):
        log_data = {
            "event": "index_sync",
            "request_id": str(uuid.uuid4()),
            "stats": stats,
            "duration_ms": round(duration * 1000, 2),
        }
        if error:
            log_data["error"] = str(error)
            self.logger.error(json.dumps(log_data))
        else:
            self.logger.info(json.dumps(log_data))

    def log_health(self, status, details):
        log_data = {
            "event": "health_check",
            "status": status,
            "details": details
        }
        if status == "healthy":
            self.logger.info(json.dumps(log_data))
        else:
            self.logger.warning(json.dumps(log_data))

logger = StructuredLogger()
