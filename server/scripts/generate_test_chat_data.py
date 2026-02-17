#!/usr/bin/env python3
"""Generate test chat data for virtual scrolling and pagination testing."""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_factory
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User


async def create_test_conversation(db: AsyncSession, user_id: str, title: str) -> Conversation:
    """Create a test conversation."""
    conv = Conversation(
        id=uuid4(),
        user_id=user_id,
        title=title,
        is_pinned=False,
        is_deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def generate_messages(
    db: AsyncSession,
    conversation_id: str,
    user_id: str,
    count: int = 500,
    start_time: datetime | None = None,
) -> int:
    """Generate a large number of test messages for a conversation.

    Args:
        db: Database session
        conversation_id: Target conversation ID
        user_id: User ID for the conversation owner
        count: Number of message pairs to generate (default 500 = 1000 total messages)
        start_time: Starting timestamp (defaults to 30 days ago)

    Returns:
        Number of messages created
    """
    if start_time is None:
        start_time = datetime.now(timezone.utc) - timedelta(days=30)

    # Sample conversation content for variety
    user_questions = [
        "请问北京师范大学的录取分数线是多少？",
        "学校有哪些优势专业？",
        "宿舍条件怎么样？",
        "奖学金申请条件是什么？",
        "如何申请转专业？",
        "校园一卡通怎么办理？",
        "图书馆开放时间是什么时候？",
        "食堂有哪些好吃的？",
        "如何参加社团活动？",
        "毕业就业情况如何？",
        "研究生推免政策是怎样的？",
        "国际学生如何申请？",
        "学费和住宿费是多少？",
        "学校地理位置怎么样？",
        "周边有什么好玩的地方？",
        "校医院怎么挂号？",
        "心理咨询服务怎么预约？",
        "如何申请助学贷款？",
        "暑期学校有哪些课程？",
        "交换生项目有哪些？",
    ]

    ai_responses = [
        "北京师范大学的录取分数线因专业和省份而异，一般在600-650分之间。具体可以查看招生网。",
        "我校有教育学、心理学、中国语言文学、历史学等多个优势学科，均在全国排名前列。",
        "学校宿舍分为4人间和6人间，配备空调、独立卫生间，环境整洁舒适。",
        "奖学金评选主要依据学业成绩、综合素质和社会实践表现，具体要求请查看学生手册。",
        "转专业一般在第二学期申请，需要达到一定的学分绩点要求并通过面试。",
        "新生入学后统一办理校园一卡通，可在食堂、图书馆、超市等场所使用。",
        "图书馆周一至周日7:00-22:00开放，考试周会延长开放时间至24:00。",
        "学校有学一、学二、学三等多个食堂，提供各地风味美食，价格亲民。",
        "开学初会有百团大战，各社团现场招新，可以根据自己的兴趣选择加入。",
        "我校毕业生就业率保持在95%以上，主要去向包括教育、金融、IT、公务员等领域。",
        "推免需要前三年成绩排名前30%，通过夏令营或预推免考核，获得导师认可。",
        "国际学生需通过HSK考试，提交成绩单和推荐信，具体要求见国际交流与合作处网站。",
        "本科生学费每年5000-6000元，住宿费800-1200元/年，具体以录取通知书为准。",
        "学校位于北京市海淀区，紧邻地铁2号线和19号线，交通便利。",
        "附近有圆明园、颐和园、中关村等景点和商业区，周末可以去逛逛。",
        "校医院实行预约制，可通过微信公众号或现场挂号，持学生证就诊。",
        "心理咨询中心提供免费咨询服务，可通过电话或网上预约，保护隐私。",
        "助学贷款分为生源地贷款和校园地贷款，入学后可向学生资助中心咨询办理。",
        "暑期学校开设通识课程和专业选修课，可以修读学分或拓展兴趣。",
        "我校与全球200多所高校建立合作关系，可申请一学期或一学年的交换项目。",
    ]

    messages_created = 0
    current_time = start_time

    for i in range(count):
        # Alternate between user and assistant messages
        # Each "turn" consists of a user question and AI response

        # User message
        user_msg = Message(
            id=uuid4(),
            conversation_id=conversation_id,
            role="user",
            content=user_questions[i % len(user_questions)],
            created_at=current_time,
            is_deleted=False,
        )
        db.add(user_msg)
        messages_created += 1

        # Increment time by 1-3 minutes for user message
        current_time += timedelta(minutes=1 + (i % 3))

        # AI response
        ai_msg = Message(
            id=uuid4(),
            conversation_id=conversation_id,
            role="assistant",
            content=ai_responses[i % len(ai_responses)],
            created_at=current_time,
            is_deleted=False,
            model_version="qwen-max",
            risk_level="low",
            review_passed=True,
        )
        db.add(ai_msg)
        messages_created += 1

        # Increment time by 30 seconds to 2 minutes for AI response
        current_time += timedelta(seconds=30 + (i % 90))

        # Commit every 100 messages to avoid memory issues
        if i % 50 == 0:
            await db.commit()
            print(f"  Created {messages_created} messages...")

    await db.commit()
    return messages_created


async def get_or_create_test_user(db: AsyncSession) -> User:
    """Get existing test user or create a new one."""
    # Try to find existing test user
    result = await db.execute(
        select(User).where(User.phone == "13800138000")
    )
    user = result.scalar_one_or_none()

    if user:
        print(f"Using existing test user: {user.id}")
        return user

    # Create new test user
    user = User(
        id=uuid4(),
        phone="13800138000",
        nickname="测试用户",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    print(f"Created new test user: {user.id}")
    return user


async def main():
    """Main entry point."""
    print("=" * 60)
    print("Test Chat Data Generator")
    print("=" * 60)

    # Parse arguments
    message_count = 500  # Default: 500 pairs = 1000 messages
    if len(sys.argv) > 1:
        try:
            message_count = int(sys.argv[1])
        except ValueError:
            print(f"Usage: {sys.argv[0]} [message_pairs_count]")
            print("  message_pairs_count: Number of Q&A pairs to generate (default: 500)")
            sys.exit(1)

    total_messages = message_count * 2
    print(f"\nConfiguration:")
    print(f"  Message pairs: {message_count}")
    print(f"  Total messages: {total_messages}")
    print(f"  Expected pages: {(total_messages // 20) + 1}")
    print()

    session_factory = get_session_factory()
    async with session_factory() as db:
        # Get or create test user
        user = await get_or_create_test_user(db)

        # Create test conversation
        print("\nCreating test conversation...")
        conv = await create_test_conversation(
            db,
            user_id=user.id,
            title=f"超长测试对话 ({total_messages}条消息)",
        )
        print(f"  Conversation ID: {conv.id}")

        # Generate messages
        print(f"\nGenerating {total_messages} messages...")
        start_time = datetime.now(timezone.utc) - timedelta(days=30)
        created = await generate_messages(
            db,
            conversation_id=conv.id,
            user_id=user.id,
            count=message_count,
            start_time=start_time,
        )

        print(f"\n{'=' * 60}")
        print("Success!")
        print(f"{'=' * 60}")
        print(f"Created {created} messages in conversation: {conv.id}")
        print(f"\nTo test pagination:")
        print(f"  1. Login as test user (phone: 13800138000)")
        print(f"  2. Open conversation: {conv.id}")
        print(f"  3. Scroll up to trigger infinite scroll loading")
        print(f"  4. Should load in batches of 20 messages")


if __name__ == "__main__":
    asyncio.run(main())
