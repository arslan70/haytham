"""
Performance monitoring utilities for swarm execution.

This module provides comprehensive performance monitoring for swarm-based
agent orchestration, tracking:
- Execution time and latency
- Token usage and costs
- Agent handoff patterns
- Context size and growth
- Timeout parameter effectiveness
- Agent participation frequency

Requirements: 4.1, 4.2, 4.3, 4.4, 6.5
"""

import json
import logging
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentExecutionMetrics:
    """Metrics for a single agent execution."""

    agent_name: str
    start_time: float
    end_time: float
    duration_seconds: float
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    context_size_chars: int = 0
    handoff_to: str | None = None
    completed_task: bool = False
    error: str | None = None


@dataclass
class SwarmExecutionMetrics:
    """Comprehensive metrics for a swarm execution."""

    swarm_type: str  # "bootstrap" or "poc_transformation"
    start_time: float
    end_time: float
    total_duration_seconds: float

    # Execution counts
    total_iterations: int = 0
    total_handoffs: int = 0

    # Token usage
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0

    # Agent metrics
    agent_executions: list[AgentExecutionMetrics] = field(default_factory=list)
    agent_participation_count: dict[str, int] = field(default_factory=dict)
    agent_total_duration: dict[str, float] = field(default_factory=dict)
    agent_total_tokens: dict[str, int] = field(default_factory=dict)

    # Handoff patterns
    handoff_sequence: list[str] = field(default_factory=list)
    handoff_pairs: list[tuple[str, str]] = field(default_factory=list)

    # Context tracking
    max_context_size_chars: int = 0
    avg_context_size_chars: float = 0.0
    context_growth_rate: float = 0.0

    # Status
    status: str = "UNKNOWN"  # COMPLETED, FAILED, TIMEOUT, ERROR
    error_message: str | None = None

    # Timeout effectiveness
    execution_timeout_used: float = 0.0
    node_timeout_used: float = 0.0
    max_handoffs_limit: int = 0
    max_iterations_limit: int = 0
    timeout_triggered: bool = False
    handoff_limit_triggered: bool = False
    iteration_limit_triggered: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert agent_executions to list of dicts
        data["agent_executions"] = [asdict(ae) for ae in self.agent_executions]
        return data


class PerformanceMonitor:
    """
    Monitor and track swarm execution performance.

    This class provides comprehensive performance monitoring for swarm-based
    agent orchestration, including:
    - Real-time metrics collection during execution
    - Post-execution analysis and reporting
    - Performance optimization recommendations
    - Historical metrics tracking
    """

    def __init__(self, log_dir: str = "haytham/logs/performance"):
        """
        Initialize performance monitor.

        Args:
            log_dir: Directory for performance logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Current execution tracking
        self.current_metrics: SwarmExecutionMetrics | None = None
        self.execution_start_time: float | None = None

        logger.info(f"PerformanceMonitor initialized with log_dir: {self.log_dir}")

    def start_monitoring(
        self,
        swarm_type: str,
        max_handoffs: int,
        max_iterations: int,
        execution_timeout: float,
        node_timeout: float,
    ) -> None:
        """
        Start monitoring a swarm execution.

        Args:
            swarm_type: Type of swarm ("bootstrap" or "poc_transformation")
            max_handoffs: Maximum handoffs limit
            max_iterations: Maximum iterations limit
            execution_timeout: Total execution timeout in seconds
            node_timeout: Per-agent timeout in seconds
        """
        self.execution_start_time = time.time()

        self.current_metrics = SwarmExecutionMetrics(
            swarm_type=swarm_type,
            start_time=self.execution_start_time,
            end_time=0.0,
            total_duration_seconds=0.0,
            max_handoffs_limit=max_handoffs,
            max_iterations_limit=max_iterations,
            execution_timeout_used=execution_timeout,
            node_timeout_used=node_timeout,
        )

        logger.info(
            f"Started monitoring {swarm_type} swarm execution "
            f"(max_handoffs={max_handoffs}, max_iterations={max_iterations}, "
            f"execution_timeout={execution_timeout}s, node_timeout={node_timeout}s)"
        )

    def record_agent_execution(
        self,
        agent_name: str,
        duration_seconds: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        context_size_chars: int = 0,
        handoff_to: str | None = None,
        completed_task: bool = False,
        error: str | None = None,
    ) -> None:
        """
        Record metrics for a single agent execution.

        Args:
            agent_name: Name of the agent
            duration_seconds: Execution duration in seconds
            input_tokens: Input tokens consumed
            output_tokens: Output tokens generated
            context_size_chars: Size of shared context in characters
            handoff_to: Name of agent handed off to (if any)
            completed_task: Whether agent completed the swarm task
            error: Error message (if any)
        """
        if not self.current_metrics:
            logger.warning("No active monitoring session, skipping agent execution record")
            return

        # Create agent execution metrics
        end_time = time.time()
        start_time = end_time - duration_seconds

        agent_metrics = AgentExecutionMetrics(
            agent_name=agent_name,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            context_size_chars=context_size_chars,
            handoff_to=handoff_to,
            completed_task=completed_task,
            error=error,
        )

        # Add to execution list
        self.current_metrics.agent_executions.append(agent_metrics)

        # Update participation count
        if agent_name not in self.current_metrics.agent_participation_count:
            self.current_metrics.agent_participation_count[agent_name] = 0
        self.current_metrics.agent_participation_count[agent_name] += 1

        # Update total duration
        if agent_name not in self.current_metrics.agent_total_duration:
            self.current_metrics.agent_total_duration[agent_name] = 0.0
        self.current_metrics.agent_total_duration[agent_name] += duration_seconds

        # Update total tokens
        if agent_name not in self.current_metrics.agent_total_tokens:
            self.current_metrics.agent_total_tokens[agent_name] = 0
        self.current_metrics.agent_total_tokens[agent_name] += agent_metrics.total_tokens

        # Update handoff tracking
        if handoff_to:
            self.current_metrics.handoff_sequence.append(agent_name)
            self.current_metrics.handoff_pairs.append((agent_name, handoff_to))
            self.current_metrics.total_handoffs += 1

        # Update context size tracking
        if context_size_chars > self.current_metrics.max_context_size_chars:
            self.current_metrics.max_context_size_chars = context_size_chars

        logger.debug(
            f"Recorded execution for {agent_name}: "
            f"{duration_seconds:.2f}s, {agent_metrics.total_tokens} tokens, "
            f"context: {context_size_chars} chars"
        )

    def end_monitoring(
        self,
        status: str,
        total_iterations: int,
        total_input_tokens: int = 0,
        total_output_tokens: int = 0,
        error_message: str | None = None,
        timeout_triggered: bool = False,
        handoff_limit_triggered: bool = False,
        iteration_limit_triggered: bool = False,
    ) -> SwarmExecutionMetrics:
        """
        End monitoring and finalize metrics.

        Args:
            status: Final execution status
            total_iterations: Total number of iterations
            total_input_tokens: Total input tokens consumed
            total_output_tokens: Total output tokens generated
            error_message: Error message (if any)
            timeout_triggered: Whether execution timeout was triggered
            handoff_limit_triggered: Whether handoff limit was triggered
            iteration_limit_triggered: Whether iteration limit was triggered

        Returns:
            Final SwarmExecutionMetrics
        """
        if not self.current_metrics:
            logger.warning("No active monitoring session to end")
            return None

        # Finalize metrics
        self.current_metrics.end_time = time.time()
        self.current_metrics.total_duration_seconds = (
            self.current_metrics.end_time - self.current_metrics.start_time
        )
        self.current_metrics.status = status
        self.current_metrics.total_iterations = total_iterations
        self.current_metrics.total_input_tokens = total_input_tokens
        self.current_metrics.total_output_tokens = total_output_tokens
        self.current_metrics.total_tokens = total_input_tokens + total_output_tokens
        self.current_metrics.error_message = error_message
        self.current_metrics.timeout_triggered = timeout_triggered
        self.current_metrics.handoff_limit_triggered = handoff_limit_triggered
        self.current_metrics.iteration_limit_triggered = iteration_limit_triggered

        # Calculate average context size
        if self.current_metrics.agent_executions:
            total_context = sum(
                ae.context_size_chars for ae in self.current_metrics.agent_executions
            )
            self.current_metrics.avg_context_size_chars = total_context / len(
                self.current_metrics.agent_executions
            )

            # Calculate context growth rate
            if len(self.current_metrics.agent_executions) > 1:
                first_context = self.current_metrics.agent_executions[0].context_size_chars
                last_context = self.current_metrics.agent_executions[-1].context_size_chars
                if first_context > 0:
                    self.current_metrics.context_growth_rate = (
                        last_context - first_context
                    ) / first_context

        logger.info(
            f"Ended monitoring: {status}, "
            f"duration={self.current_metrics.total_duration_seconds:.2f}s, "
            f"iterations={total_iterations}, "
            f"tokens={self.current_metrics.total_tokens}"
        )

        # Save metrics to file
        self._save_metrics()

        # Generate performance report
        self._generate_performance_report()

        metrics = self.current_metrics
        self.current_metrics = None
        self.execution_start_time = None

        return metrics

    def _save_metrics(self) -> None:
        """Save metrics to JSON file."""
        if not self.current_metrics:
            return

        timestamp = datetime.fromtimestamp(self.current_metrics.start_time).strftime(
            "%Y%m%d_%H%M%S"
        )
        filename = f"swarm_metrics_{self.current_metrics.swarm_type}_{timestamp}.json"
        filepath = self.log_dir / filename

        try:
            with open(filepath, "w") as f:
                json.dump(self.current_metrics.to_dict(), f, indent=2)
            logger.info(f"Saved performance metrics to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save metrics to {filepath}: {e}")

    def _generate_performance_report(self) -> None:
        """Generate human-readable performance report."""
        if not self.current_metrics:
            return

        m = self.current_metrics

        # Generate report
        report_lines = [
            "=" * 80,
            f"SWARM PERFORMANCE REPORT - {m.swarm_type.upper()}",
            "=" * 80,
            "",
            "EXECUTION SUMMARY",
            "-" * 80,
            f"Status: {m.status}",
            f"Duration: {m.total_duration_seconds:.2f}s",
            f"Iterations: {m.total_iterations}",
            f"Handoffs: {m.total_handoffs}",
            "",
            "TOKEN USAGE",
            "-" * 80,
            f"Input Tokens: {m.total_input_tokens:,}",
            f"Output Tokens: {m.total_output_tokens:,}",
            f"Total Tokens: {m.total_tokens:,}",
            f"Estimated Cost: ${self._estimate_cost(m.total_tokens):.4f}",
            "",
            "AGENT PARTICIPATION",
            "-" * 80,
        ]

        # Sort agents by participation count
        sorted_agents = sorted(
            m.agent_participation_count.items(), key=lambda x: x[1], reverse=True
        )

        for agent_name, count in sorted_agents:
            duration = m.agent_total_duration.get(agent_name, 0.0)
            tokens = m.agent_total_tokens.get(agent_name, 0)
            report_lines.append(
                f"  {agent_name}: {count} executions, {duration:.2f}s total, {tokens:,} tokens"
            )

        report_lines.extend(
            [
                "",
                "CONTEXT TRACKING",
                "-" * 80,
                f"Max Context Size: {m.max_context_size_chars:,} chars",
                f"Avg Context Size: {m.avg_context_size_chars:,.0f} chars",
                f"Context Growth Rate: {m.context_growth_rate:.1%}",
                "",
                "TIMEOUT PARAMETERS",
                "-" * 80,
                f"Execution Timeout: {m.execution_timeout_used:.0f}s (triggered: {m.timeout_triggered})",
                f"Node Timeout: {m.node_timeout_used:.0f}s",
                f"Max Handoffs: {m.max_handoffs_limit} (triggered: {m.handoff_limit_triggered})",
                f"Max Iterations: {m.max_iterations_limit} (triggered: {m.iteration_limit_triggered})",
                "",
            ]
        )

        # Add handoff pattern analysis
        if m.handoff_pairs:
            report_lines.extend(
                [
                    "HANDOFF PATTERNS",
                    "-" * 80,
                ]
            )

            # Count handoff pairs
            pair_counts = Counter(m.handoff_pairs)
            sorted_pairs = sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)

            for (from_agent, to_agent), count in sorted_pairs[:10]:  # Top 10
                report_lines.append(f"  {from_agent} → {to_agent}: {count} times")

            report_lines.append("")

        # Add optimization recommendations
        recommendations = self._generate_recommendations()
        if recommendations:
            report_lines.extend(
                [
                    "OPTIMIZATION RECOMMENDATIONS",
                    "-" * 80,
                ]
            )
            for rec in recommendations:
                report_lines.append(f"  • {rec}")
            report_lines.append("")

        report_lines.append("=" * 80)

        # Write report to file
        timestamp = datetime.fromtimestamp(m.start_time).strftime("%Y%m%d_%H%M%S")
        filename = f"swarm_report_{m.swarm_type}_{timestamp}.txt"
        filepath = self.log_dir / filename

        try:
            with open(filepath, "w") as f:
                f.write("\n".join(report_lines))
            logger.info(f"Generated performance report: {filepath}")
        except Exception as e:
            logger.error(f"Failed to write performance report to {filepath}: {e}")

    def _estimate_cost(self, total_tokens: int) -> float:
        """
        Estimate cost based on token usage.

        Uses Claude Sonnet 4.5 pricing:
        - Input: $3.00 per million tokens
        - Output: $15.00 per million tokens

        For simplicity, uses average of $9.00 per million tokens.

        Args:
            total_tokens: Total token count

        Returns:
            Estimated cost in USD
        """
        # Average cost per million tokens
        cost_per_million = 9.00
        return (total_tokens / 1_000_000) * cost_per_million

    def _generate_recommendations(self) -> list[str]:
        """
        Generate optimization recommendations based on metrics.

        Returns:
            List of recommendation strings
        """
        if not self.current_metrics:
            return []

        m = self.current_metrics
        recommendations = []

        # Check if timeout parameters are too loose
        if m.total_duration_seconds < m.execution_timeout_used * 0.5:
            recommendations.append(
                f"Execution timeout ({m.execution_timeout_used:.0f}s) could be reduced to "
                f"~{m.total_duration_seconds * 1.5:.0f}s based on actual execution time"
            )

        # Check if handoff limit is too high
        if m.total_handoffs < m.max_handoffs_limit * 0.5:
            recommendations.append(
                f"Max handoffs limit ({m.max_handoffs_limit}) could be reduced to "
                f"~{int(m.total_handoffs * 1.5)} based on actual handoffs"
            )

        # Check for context growth
        if m.context_growth_rate > 2.0:
            recommendations.append(
                f"Context size grew by {m.context_growth_rate:.0%}. "
                "Consider implementing context summarization to reduce token usage"
            )

        # Check for repetitive agent participation
        if m.agent_participation_count:
            max_participation = max(m.agent_participation_count.values())
            if max_participation > 3:
                agent_name = [
                    name
                    for name, count in m.agent_participation_count.items()
                    if count == max_participation
                ][0]
                recommendations.append(
                    f"Agent '{agent_name}' executed {max_participation} times. "
                    "Consider reviewing handoff logic to prevent excessive re-execution"
                )

        # Check for timeout triggers
        if m.timeout_triggered:
            recommendations.append(
                "Execution timeout was triggered. Consider increasing timeout or "
                "optimizing agent prompts for faster execution"
            )

        if m.handoff_limit_triggered:
            recommendations.append(
                "Handoff limit was triggered. Review agent handoff logic to ensure "
                "proper task completion without excessive transfers"
            )

        # Check token usage efficiency
        if m.agent_executions:
            avg_tokens_per_agent = m.total_tokens / len(m.agent_executions)
            if avg_tokens_per_agent > 10000:
                recommendations.append(
                    f"Average tokens per agent execution is high ({avg_tokens_per_agent:,.0f}). "
                    "Consider optimizing prompts or implementing context summarization"
                )

        return recommendations

    def get_current_metrics(self) -> SwarmExecutionMetrics | None:
        """Get current metrics (if monitoring is active)."""
        return self.current_metrics


# Global performance monitor instance
_performance_monitor: PerformanceMonitor | None = None


def get_performance_monitor() -> PerformanceMonitor:
    """
    Get or create global performance monitor instance.

    Returns:
        PerformanceMonitor instance
    """
    global _performance_monitor

    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
        logger.info("Created global PerformanceMonitor instance")

    return _performance_monitor
