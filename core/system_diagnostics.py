"""
FRANKENSTEIN 1.0 - System Diagnostics
Phase 2: Hardware Health Diagnostics

Purpose: Analyze system resources and provide actionable recommendations
"""

import subprocess
import re
from typing import Dict, Any, List, Tuple, Callable
from dataclasses import dataclass


@dataclass
class ProcessInfo:
    """Information about a running process"""
    name: str
    pid: int
    memory_mb: float


@dataclass 
class SystemStats:
    """System memory and CPU statistics"""
    total_memory_mb: float
    available_memory_mb: float
    used_memory_mb: float
    memory_percent: float
    cpu_percent: float


def get_system_stats() -> SystemStats:
    """Get current system memory and CPU stats"""
    try:
        # Get memory info
        result = subprocess.run(
            ['systeminfo'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        total_mb = 8000.0
        available_mb = 2000.0
        
        for line in result.stdout.split('\n'):
            if 'Total Physical Memory' in line:
                match = re.search(r'([\d,]+)\s*MB', line)
                if match:
                    total_mb = float(match.group(1).replace(',', ''))
            elif 'Available Physical Memory' in line:
                match = re.search(r'([\d,]+)\s*MB', line)
                if match:
                    available_mb = float(match.group(1).replace(',', ''))
        
        used_mb = total_mb - available_mb
        memory_percent = (used_mb / total_mb) * 100 if total_mb > 0 else 0
        
        # Get CPU
        cpu_result = subprocess.run(
            ['wmic', 'cpu', 'get', 'loadpercentage'],
            capture_output=True,
            text=True,
            timeout=10
        )
        cpu_percent = 0.0
        for line in cpu_result.stdout.split('\n'):
            line = line.strip()
            if line.isdigit():
                cpu_percent = float(line)
                break
        
        return SystemStats(
            total_memory_mb=total_mb,
            available_memory_mb=available_mb,
            used_memory_mb=used_mb,
            memory_percent=memory_percent,
            cpu_percent=cpu_percent
        )
    except Exception as e:
        return SystemStats(0, 0, 0, 0, 0)


def get_top_processes(limit: int = 15) -> List[ProcessInfo]:
    """Get top memory-consuming processes"""
    try:
        result = subprocess.run(
            ['tasklist', '/FO', 'CSV'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        processes = []
        for line in result.stdout.split('\n'):
            if line.startswith('"') and 'Image Name' not in line:
                parts = line.strip().split('","')
                if len(parts) >= 5:
                    name = parts[0].strip('"')
                    try:
                        pid = int(parts[1].strip('"'))
                    except:
                        pid = 0
                    mem_str = parts[4].strip('"').replace(',', '').replace(' K', '')
                    try:
                        mem_kb = float(mem_str)
                        mem_mb = mem_kb / 1024
                    except:
                        mem_mb = 0
                    
                    processes.append(ProcessInfo(name, pid, mem_mb))
        
        # Sort by memory descending
        processes.sort(key=lambda p: p.memory_mb, reverse=True)
        
        # Aggregate by process name
        aggregated = {}
        for p in processes:
            base_name = p.name.replace('.exe', '')
            if base_name in aggregated:
                aggregated[base_name]['memory'] += p.memory_mb
                aggregated[base_name]['count'] += 1
            else:
                aggregated[base_name] = {'memory': p.memory_mb, 'count': 1, 'name': p.name}
        
        # Convert back to list and sort
        result_list = []
        for name, data in aggregated.items():
            result_list.append(ProcessInfo(
                name=data['name'],
                pid=data['count'],  # Using PID field for count
                memory_mb=data['memory']
            ))
        
        result_list.sort(key=lambda p: p.memory_mb, reverse=True)
        return result_list[:limit]
        
    except Exception as e:
        return []


def generate_recommendations(stats: SystemStats, processes: List[ProcessInfo]) -> List[Dict[str, str]]:
    """Generate actionable recommendations based on system state"""
    recommendations = []
    
    # Memory-based recommendations
    if stats.memory_percent > 80:
        recommendations.append({
            'priority': 'HIGH',
            'issue': 'Critical memory usage (>80%)',
            'action': 'Close unnecessary applications immediately',
            'command': None
        })
    elif stats.memory_percent > 70:
        recommendations.append({
            'priority': 'MEDIUM',
            'issue': 'High memory usage (>70%)',
            'action': 'Consider closing some applications',
            'command': None
        })
    
    # Process-specific recommendations
    for proc in processes[:5]:
        if 'msedge' in proc.name.lower() and proc.memory_mb > 500:
            recommendations.append({
                'priority': 'MEDIUM',
                'issue': f'Edge browser using {proc.memory_mb:.0f} MB',
                'action': 'Close unused browser tabs',
                'command': None
            })
        elif 'claude' in proc.name.lower() and proc.memory_mb > 1000:
            recommendations.append({
                'priority': 'LOW',
                'issue': f'Claude Desktop using {proc.memory_mb:.0f} MB',
                'action': 'Restart Claude Desktop to free memory',
                'command': 'taskkill /F /IM claude.exe & start claude'
            })
        elif 'notion' in proc.name.lower():
            recommendations.append({
                'priority': 'MEDIUM', 
                'issue': f'Notion using {proc.memory_mb:.0f} MB',
                'action': 'Close Notion if not in use',
                'command': 'taskkill /F /IM Notion.exe'
            })
        elif 'teams' in proc.name.lower() and proc.memory_mb > 300:
            recommendations.append({
                'priority': 'LOW',
                'issue': f'Teams using {proc.memory_mb:.0f} MB',
                'action': 'Close Teams if not in a meeting',
                'command': 'taskkill /F /IM Teams.exe'
            })
        elif 'slack' in proc.name.lower() and proc.memory_mb > 300:
            recommendations.append({
                'priority': 'LOW',
                'issue': f'Slack using {proc.memory_mb:.0f} MB', 
                'action': 'Close Slack if not needed',
                'command': 'taskkill /F /IM slack.exe'
            })
    
    # Windows feature recommendations
    for proc in processes:
        if 'widgets' in proc.name.lower() and proc.memory_mb > 50:
            recommendations.append({
                'priority': 'LOW',
                'issue': 'Windows Widgets running',
                'action': 'Disable Widgets in Taskbar settings',
                'command': None
            })
            break
    
    # Add general tips if memory is high
    if stats.memory_percent > 65:
        recommendations.append({
            'priority': 'TIP',
            'issue': 'General optimization',
            'action': 'Restart your PC to clear memory fragmentation',
            'command': None
        })
    
    return recommendations


def kill_process(process_name: str) -> Tuple[bool, str]:
    """Kill a process by name"""
    try:
        result = subprocess.run(
            ['taskkill', '/F', '/IM', process_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True, f"Successfully terminated {process_name}"
        else:
            return False, f"Failed to terminate: {result.stderr}"
    except Exception as e:
        return False, f"Error: {str(e)}"


def format_diagnosis_report(stats: SystemStats, processes: List[ProcessInfo], 
                           recommendations: List[Dict[str, str]]) -> str:
    """Format the full diagnosis report for terminal display"""
    lines = [
        "",
        "╔══════════════════════════════════════════════════════════════════╗",
        "║              🔍 SYSTEM DIAGNOSIS REPORT                          ║",
        "╠══════════════════════════════════════════════════════════════════╣",
        "║  MEMORY STATUS                                                   ║",
        f"║    Total:     {stats.total_memory_mb:,.0f} MB ({stats.total_memory_mb/1024:.1f} GB)                            ║",
        f"║    Used:      {stats.used_memory_mb:,.0f} MB ({stats.memory_percent:.1f}%)                              ║",
        f"║    Available: {stats.available_memory_mb:,.0f} MB                                      ║",
        f"║    CPU Load:  {stats.cpu_percent:.0f}%                                                 ║",
        "╠══════════════════════════════════════════════════════════════════╣",
        "║  TOP MEMORY CONSUMERS                                            ║",
    ]
    
    for i, proc in enumerate(processes[:8], 1):
        count_str = f"({proc.pid} processes)" if proc.pid > 1 else ""
        name_display = proc.name[:20] + "..." if len(proc.name) > 20 else proc.name
        lines.append(f"║    {i}. {name_display:<24} {proc.memory_mb:>7.0f} MB {count_str:<12}  ║")
    
    lines.extend([
        "╠══════════════════════════════════════════════════════════════════╣",
        "║  RECOMMENDATIONS                                                 ║",
    ])
    
    for i, rec in enumerate(recommendations[:6], 1):
        priority_icon = {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟡", "TIP": "💡"}.get(rec['priority'], "•")
        action = rec['action']
        if len(action) > 50:
            action = action[:47] + "..."
        lines.append(f"║    {priority_icon} [{rec['priority']:<6}] {action:<45}  ║")
    
    lines.extend([
        "╠══════════════════════════════════════════════════════════════════╣",
        "║  QUICK ACTIONS                                                   ║",
        "║    diagnose fix <number>  - Apply a specific fix                 ║",
        "║    diagnose kill <name>   - Kill a process by name               ║",
        "║    diagnose refresh       - Refresh diagnosis                    ║",
        "╚══════════════════════════════════════════════════════════════════╝",
        ""
    ])
    
    return "\n".join(lines)


# Store last diagnosis for fix commands
_last_recommendations: List[Dict[str, str]] = []


def handle_diagnose_command(args: List[str], write_output: Callable[[str], None]) -> None:
    """
    Handle 'diagnose' command in Monster Terminal.
    
    Usage:
        diagnose              - Run full system diagnosis
        diagnose refresh      - Refresh diagnosis
        diagnose fix <n>      - Apply recommendation #n
        diagnose kill <name>  - Kill process by name
    """
    global _last_recommendations
    
    if not args or args[0].lower() in ('', 'refresh', 'status'):
        # Run full diagnosis
        write_output("\n⏳ Running system diagnosis...\n")
        
        stats = get_system_stats()
        processes = get_top_processes(15)
        recommendations = generate_recommendations(stats, processes)
        _last_recommendations = recommendations
        
        report = format_diagnosis_report(stats, processes, recommendations)
        write_output(report)
        
    elif args[0].lower() == 'fix' and len(args) > 1:
        try:
            fix_num = int(args[1])
            if 1 <= fix_num <= len(_last_recommendations):
                rec = _last_recommendations[fix_num - 1]
                if rec.get('command'):
                    write_output(f"\n⚙️ Applying fix: {rec['action']}\n")
                    try:
                        result = subprocess.run(
                            rec['command'],
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        write_output(f"✅ Command executed\n")
                        if result.stdout:
                            write_output(f"{result.stdout}\n")
                    except Exception as e:
                        write_output(f"❌ Error: {e}\n")
                else:
                    write_output(f"\n⚠️ This fix requires manual action:\n")
                    write_output(f"   {rec['action']}\n\n")
            else:
                write_output(f"\n❌ Invalid fix number. Run 'diagnose' first.\n\n")
        except ValueError:
            write_output(f"\n❌ Invalid fix number: {args[1]}\n\n")
            
    elif args[0].lower() == 'kill' and len(args) > 1:
        process_name = args[1]
        if not process_name.endswith('.exe'):
            process_name += '.exe'
        write_output(f"\n⚙️ Terminating {process_name}...\n")
        success, message = kill_process(process_name)
        if success:
            write_output(f"✅ {message}\n\n")
        else:
            write_output(f"❌ {message}\n\n")
            
    elif args[0].lower() == 'quick':
        # Quick stats only
        stats = get_system_stats()
        write_output(f"\n📊 Quick Stats: CPU {stats.cpu_percent:.0f}% | RAM {stats.memory_percent:.0f}% ({stats.used_memory_mb:.0f}/{stats.total_memory_mb:.0f} MB)\n\n")
        
    else:
        write_output("\n❌ Unknown diagnose command\n")
        write_output("Usage: diagnose [refresh|fix <n>|kill <name>|quick]\n\n")
