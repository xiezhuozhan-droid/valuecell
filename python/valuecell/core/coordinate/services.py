"""Helper utilities for composing orchestrator service dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from valuecell.core.agent.connect import RemoteConnections
from valuecell.core.conversation import ConversationManager, SQLiteItemStore
from valuecell.core.conversation.service import ConversationService
from valuecell.core.plan.service import PlanService
from valuecell.core.response.service import ResponseService
from valuecell.core.super_agent import SuperAgentService
from valuecell.core.task.executor import TaskExecutor
from valuecell.core.task.service import TaskService
from valuecell.utils import resolve_db_path


@dataclass(frozen=True)
class AgentServiceBundle:
    """Aggregate all services required by ``AgentOrchestrator``.

    The bundle guarantees that conversation-oriented objects share the same
    ``ConversationManager`` instance so that persistence is consistent even
    when individual services are overridden by callers. This also centralises
    the default construction logic, reducing the amount of dependency wiring
    inside the orchestrator itself.
    """

    agent_connections: RemoteConnections
    conversation_service: ConversationService
    response_service: ResponseService
    task_service: TaskService
    plan_service: PlanService
    super_agent_service: SuperAgentService
    task_executor: TaskExecutor

    @property
    def conversation_manager(self) -> ConversationManager:
        """Expose the shared conversation manager used by all services."""

        return self.conversation_service.manager

    @classmethod
    def compose(
        cls,
        *,
        conversation_service: Optional[ConversationService] = None,
        response_service: Optional[ResponseService] = None,
        plan_service: Optional[PlanService] = None,
        super_agent_service: Optional[SuperAgentService] = None,
        task_executor: Optional[TaskExecutor] = None,
    ) -> "AgentServiceBundle":
        """Create a bundle, constructing any missing services with defaults."""

        connections = RemoteConnections()

        if conversation_service is not None:
            conv_service = conversation_service
        elif response_service is not None:
            conv_service = response_service.conversation_service
        else:
            base_manager = ConversationManager(
                item_store=SQLiteItemStore(resolve_db_path())
            )
            conv_service = ConversationService(manager=base_manager)

        resp_service = response_service or ResponseService(
            conversation_service=conv_service
        )
        t_service = TaskService()
        p_service = plan_service or PlanService(connections)
        sa_service = super_agent_service or SuperAgentService()
        executor = task_executor or TaskExecutor(
            agent_connections=connections,
            task_service=t_service,
            response_service=resp_service,
            conversation_service=conv_service,
        )

        return cls(
            agent_connections=connections,
            conversation_service=conv_service,
            response_service=resp_service,
            task_service=t_service,
            plan_service=p_service,
            super_agent_service=sa_service,
            task_executor=executor,
        )
