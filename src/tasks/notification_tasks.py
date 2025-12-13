"""
알림 관련 Celery 작업
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def send_email_notification(
    self, recipient: str, subject: str, body: str, html_body: str = None
) -> Dict[str, Any]:
    """
    이메일 알림 발송

    Args:
        recipient: 수신자 이메일
        subject: 제목
        body: 본문 (텍스트)
        html_body: HTML 본문 (선택적)
    """
    logger.info(
        f"Sending email notification. Task ID: {self.request.id}, To: {recipient}"
    )

    try:
        # 실제 이메일 발송 로직 구현
        # 예: SMTP, SendGrid, AWS SES 등

        # 현재는 로그만 기록
        logger.info(f"Email sent to {recipient}: {subject}")

        return {
            "success": True,
            "recipient": recipient,
            "subject": subject,
            "task_id": self.request.id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Email notification failed: {e}")
        raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def send_webhook_notification(
    self, webhook_url: str, payload: Dict[str, Any], headers: Dict[str, str] = None
) -> Dict[str, Any]:
    """
    웹훅 알림 발송

    Args:
        webhook_url: 웹훅 URL
        payload: 전송할 데이터
        headers: HTTP 헤더 (선택적)
    """
    logger.info(
        f"Sending webhook notification. Task ID: {self.request.id}, URL: {webhook_url}"
    )

    try:
        import httpx

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                webhook_url,
                json=payload,
                headers=headers or {"Content-Type": "application/json"},
            )
            response.raise_for_status()

        logger.info(f"Webhook sent to {webhook_url}: {response.status_code}")

        return {
            "success": True,
            "webhook_url": webhook_url,
            "status_code": response.status_code,
            "task_id": self.request.id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Webhook notification failed: {e}")
        raise


@shared_task(bind=True)
def send_batch_notifications(
    self, notifications: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    대량 알림 발송

    Args:
        notifications: 알림 목록
            - type: "email" | "webhook"
            - 기타 타입별 필수 필드
    """
    logger.info(
        f"Sending batch notifications. Task ID: {self.request.id}, "
        f"Count: {len(notifications)}"
    )

    results = []

    for notification in notifications:
        try:
            notif_type = notification.get("type")

            if notif_type == "email":
                task = send_email_notification.delay(
                    recipient=notification.get("recipient"),
                    subject=notification.get("subject"),
                    body=notification.get("body"),
                    html_body=notification.get("html_body"),
                )
                results.append(
                    {
                        "type": "email",
                        "task_id": task.id,
                        "recipient": notification.get("recipient"),
                    }
                )

            elif notif_type == "webhook":
                task = send_webhook_notification.delay(
                    webhook_url=notification.get("webhook_url"),
                    payload=notification.get("payload"),
                    headers=notification.get("headers"),
                )
                results.append(
                    {
                        "type": "webhook",
                        "task_id": task.id,
                        "url": notification.get("webhook_url"),
                    }
                )

            else:
                logger.warning(f"Unknown notification type: {notif_type}")
                results.append(
                    {
                        "type": notif_type,
                        "error": "Unknown notification type",
                    }
                )

        except Exception as e:
            logger.error(f"Failed to queue notification: {e}")
            results.append(
                {
                    "type": notification.get("type"),
                    "error": str(e),
                }
            )

    logger.info(f"Batch notifications queued: {len(results)} tasks")

    return {
        "success": True,
        "queued_count": len([r for r in results if "task_id" in r]),
        "failed_count": len([r for r in results if "error" in r]),
        "results": results,
        "task_id": self.request.id,
        "timestamp": datetime.utcnow().isoformat(),
    }


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def notify_creator_evaluation_complete(
    self,
    creator_id: str,
    evaluation_result: Dict[str, Any],
    notification_channels: List[str] = None,
) -> Dict[str, Any]:
    """
    크리에이터 평가 완료 알림

    Args:
        creator_id: 크리에이터 ID
        evaluation_result: 평가 결과
        notification_channels: 알림 채널 목록 (email, webhook 등)
    """
    logger.info(
        f"Notifying creator evaluation complete. Task ID: {self.request.id}, "
        f"Creator: {creator_id}"
    )

    channels = notification_channels or ["email"]
    results = []

    for channel in channels:
        if channel == "email":
            # 이메일 알림 생성
            subject = (
                f"크리에이터 평가 완료 - {evaluation_result.get('grade', 'N/A')} 등급"
            )
            body = f"""
            안녕하세요,

            크리에이터 평가가 완료되었습니다.

            평가 결과:
            - 등급: {evaluation_result.get('grade', 'N/A')}
            - 점수: {evaluation_result.get('score', 0):.1f}
            - 결정: {evaluation_result.get('decision', 'N/A')}

            자세한 내용은 대시보드에서 확인하세요.
            """

            # 실제로는 크리에이터의 이메일 주소를 조회해야 함
            task = send_email_notification.delay(
                recipient=f"creator_{creator_id}@example.com",  # 실제 이메일로 대체
                subject=subject,
                body=body,
            )
            results.append(
                {
                    "channel": "email",
                    "task_id": task.id,
                }
            )

        elif channel == "webhook":
            # 웹훅 알림 생성
            task = send_webhook_notification.delay(
                webhook_url="https://example.com/webhook",  # 실제 웹훅 URL로 대체
                payload={
                    "event": "creator_evaluation_complete",
                    "creator_id": creator_id,
                    "result": evaluation_result,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            results.append(
                {
                    "channel": "webhook",
                    "task_id": task.id,
                }
            )

    logger.info(f"Creator evaluation notifications queued: {len(results)} tasks")

    return {
        "success": True,
        "creator_id": creator_id,
        "notifications": results,
        "task_id": self.request.id,
        "timestamp": datetime.utcnow().isoformat(),
    }
