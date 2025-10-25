from unittest.mock import MagicMock

import pytest

from kirara_ai.im.message import IMMessage
from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.workflow.core.dispatch import CombinedDispatchRule, DispatchRuleRegistry, RuleGroup, SimpleDispatchRule
from kirara_ai.workflow.implementations.blocks.system.help import GenerateHelp


@pytest.fixture
def container():
    """创建一个带有模拟规则注册表的容器"""
    container = DependencyContainer()
    registry = MagicMock(spec=DispatchRuleRegistry)
    container.register(DispatchRuleRegistry, registry)
    return container, registry


def create_mock_rule(
    rule_id: str, name: str, description: str, workflow_id: str, rule_groups: list
) -> CombinedDispatchRule:
    """创建模拟的组合规则"""
    return CombinedDispatchRule(
        rule_id=rule_id,
        name=name,
        description=description,
        workflow_id=workflow_id,
        rule_groups=rule_groups,
        enabled=True,
        priority=5,
        metadata={},
    )


def test_generate_help_basic(container):
    """测试基本的帮助信息生成"""
    container, registry = container

    # 创建模拟规则
    help_rule = create_mock_rule(
        rule_id="help_command",
        name="帮助命令",
        description="显示帮助信息",
        workflow_id="system:help",
        rule_groups=[
            RuleGroup(
                operator="and",
                rules=[
                    SimpleDispatchRule(type="prefix", config={"prefix": "/help"}),
                    SimpleDispatchRule(
                        type="keyword", config={"keywords": ["帮助", "help"]}
                    ),
                ],
            )
        ],
    )

    chat_rule = create_mock_rule(
        rule_id="chat_command",
        name="聊天命令",
        description="开始聊天",
        workflow_id="chat:chat",
        rule_groups=[
            RuleGroup(
                operator="or",
                rules=[
                    SimpleDispatchRule(type="prefix", config={"prefix": "/chat"}),
                    SimpleDispatchRule(
                        type="keyword", config={"keywords": ["聊天", "对话"]}
                    ),
                ],
            )
        ],
    )

    registry.get_active_rules.return_value = [help_rule, chat_rule]

    block = GenerateHelp()
    block.container = container
    result = block.execute()

    assert "response" in result
    response = result["response"]
    assert isinstance(response, IMMessage)

    help_text = response.content

    # 检查帮助文本格式
    assert "机器人命令帮助" in help_text
    assert "SYSTEM" in help_text
    assert "CHAT" in help_text
    assert "帮助命令" in help_text
    assert "聊天命令" in help_text
    assert "/help" in help_text
    assert "/chat" in help_text
    assert "显示帮助信息" in help_text
    assert "开始聊天" in help_text
    assert "且" in help_text  # 检查组合逻辑词
    assert "或" in help_text


def test_generate_help_empty(container):
    """测试没有规则时的帮助信息生成"""
    container, registry = container
    registry.get_active_rules.return_value = []

    block = GenerateHelp()
    block.container = container
    result = block.execute()

    assert "response" in result
    response = result["response"]
    assert isinstance(response, IMMessage)
    help_text = response.content

    # 检查基本格式
    assert "机器人命令帮助" in help_text
    # 确保没有分类和命令
    assert "📑" not in help_text
    assert "🔸" not in help_text


def test_generate_help_no_description(container):
    """测试规则没有描述时的处理"""
    container, registry = container

    # 创建一个没有描述的规则
    test_rule = create_mock_rule(
        rule_id="test_command",
        name="测试命令",
        description="",  # 空描述
        workflow_id="test:test",
        rule_groups=[
            RuleGroup(
                operator="or",
                rules=[SimpleDispatchRule(type="prefix", config={"prefix": "/test"})],
            )
        ],
    )

    registry.get_active_rules.return_value = [test_rule]

    block = GenerateHelp()
    block.container = container
    result = block.execute()

    assert "response" in result
    response = result["response"]
    assert isinstance(response, IMMessage)
    help_text = response.content

    # 应该显示命令，但没有描述部分
    assert "测试命令" in help_text
    assert "/test" in help_text
    assert "说明:" not in help_text


def test_generate_help_complex_rules(container):
    """测试复杂组合规则的帮助信息生成"""
    container, registry = container

    # 创建一个包含复杂组合条件的规则
    complex_rule = create_mock_rule(
        rule_id="complex_command",
        name="复杂命令",
        description="这是一个复杂的命令",
        workflow_id="test:complex",
        rule_groups=[
            RuleGroup(
                operator="or",
                rules=[
                    SimpleDispatchRule(type="prefix", config={"prefix": "/complex"}),
                    SimpleDispatchRule(
                        type="keyword", config={"keywords": ["复杂", "高级"]}
                    ),
                ],
            ),
            RuleGroup(
                operator="and",
                rules=[
                    SimpleDispatchRule(type="regex", config={"pattern": ".*test.*"}),
                    SimpleDispatchRule(type="keyword", config={"keywords": ["测试"]}),
                ],
            ),
        ],
    )

    registry.get_active_rules.return_value = [complex_rule]

    block = GenerateHelp()
    block.container = container
    result = block.execute()

    help_text = result["response"].content

    # 检查复杂规则的格式
    assert "复杂命令" in help_text
    assert "这是一个复杂的命令" in help_text
    assert "输入以 /complex 开头" in help_text
    assert "输入包含 复杂 或 高级" in help_text
    assert "输入匹配正则 .*test.*" in help_text
    assert "输入包含 测试" in help_text
    assert "并且" in help_text
    assert "或" in help_text 