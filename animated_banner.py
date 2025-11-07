import os
import time
import sys
import random

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def typewriter(text, delay=0.03, color=Colors.WHITE, end='\n'):
    """Typewriter effect for text"""
    for char in text:
        print(color + char + Colors.END, end='', flush=True)
        time.sleep(delay)
    print(end, end='')

def animate_banner():
    """Animated ASCII banner"""
    banner = [
        f"{Colors.CYAN}╔══════════════════════════════════════════════════════════════╗",
        f"║                                                              ║",
        f"║  █████╗ ██╗     ██╗ █████╗ ███████╗███████╗███████╗         ║",
        f"║ ██╔══██╗██║     ██║██╔══██╗██╔════╝██╔════╝██╔════╝         ║",
        f"║ ███████║██║     ██║███████║███████╗███████╗███████╗         ║",
        f"║ ██╔══██║██║     ██║██╔══██║╚════██║╚════██║╚════██║         ║",
        f"║ ██║  ██║███████╗██║██║  ██║███████║███████║███████║         ║",
        f"║ ╚═╝  ╚═╝╚══════╝╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝         ║",
        f"║                                                              ║",
        f"║ 📧 Telegram Email Alias Manager Bot by @the_BR_king           ║",
        f"║                                                              ║",
        f"╚══════════════════════════════════════════════════════════════╝{Colors.END}"
    ]
    
    for line in banner:
        typewriter(line, 0.01, Colors.CYAN)

def loading_animation(text, duration=2):
    """Loading animation with dots"""
    print(f"\n{Colors.YELLOW}{text}", end='', flush=True)
    for _ in range(duration * 4):
        print('.', end='', flush=True)
        time.sleep(0.25)
    print(f"{Colors.GREEN} ✓{Colors.END}")

def feature_showcase():
    """Animated feature showcase"""
    features = [
        {
            "icon": "🔒",
            "title": "Plus Addressing",
            "desc": "email+random123@domain.com",
            "color": Colors.GREEN
        },
        {
            "icon": "⚡", 
            "title": "Dot Variants",
            "desc": "y.o.u.r.e.m.a.i.l@domain.com",
            "color": Colors.BLUE
        },
        {
            "icon": "🎯",
            "title": "Custom Aliases", 
            "desc": "randomtag@yourdomain.com",
            "color": Colors.MAGENTA
        }
    ]
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}🚀 Features:{Colors.END}\n")
    
    for i, feature in enumerate(features):
        time.sleep(0.3)
        print(f"  {feature['color']}{feature['icon']} {feature['title']}{Colors.END}")
        typewriter(f"     {feature['desc']}", 0.02, Colors.WHITE)
        print()

def system_info():
    """Display system information"""
    print(f"\n{Colors.BOLD}{Colors.YELLOW}📊 System Information:{Colors.END}\n")
    
    info_items = [
        ("Python Version", f"{sys.version.split()[0]}", Colors.GREEN),
        ("Platform", f"{sys.platform}", Colors.BLUE),
        ("Bot Version", "2.0.0", Colors.MAGENTA),
        ("Developer", "DEVIL BGMI", Colors.CYAN)
    ]
    
    for label, value, color in info_items:
        print(f"  {Colors.WHITE}{label}: {color}{value}{Colors.END}")
        time.sleep(0.2)

def commands_preview():
    """Preview of available commands"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}📋 Quick Commands:{Colors.END}\n")
    
    commands = [
        ("/start", "Start the bot", Colors.GREEN),
        ("/set email", "Set your base email", Colors.BLUE),
        ("/generate", "Create email aliases", Colors.MAGENTA),
        ("/list", "View your aliases", Colors.YELLOW),
        ("/help", "Show all commands", Colors.CYAN)
    ]
    
    for cmd, desc, color in commands:
        typewriter(f"  {color}{cmd:<15} {Colors.WHITE}{desc}{Colors.END}", 0.01)
        time.sleep(0.1)

def progress_bar(description, duration=3):
    """Animated progress bar"""
    print(f"\n{Colors.YELLOW}{description}{Colors.END}")
    print(f"{Colors.BLUE}[{Colors.END}", end='', flush=True)
    
    bar_length = 30
    for i in range(bar_length + 1):
        progress = i / bar_length
        bars = '█' * i
        spaces = ' ' * (bar_length - i)
        percentage = int(progress * 100)
        
        print(f'\r{Colors.BLUE}[{Colors.GREEN}{bars}{spaces}{Colors.BLUE}] {percentage}%{Colors.END}', end='', flush=True)
        time.sleep(duration / bar_length)
    
    print(f" {Colors.GREEN}✓{Colors.END}")

def matrix_effect(lines=10, duration=2):
    """Cool matrix-like falling characters effect"""
    chars = "01█▓▒░┃┆┇┊┋╌╍╎╏┌┐└┘├┤┬┴┼╭╮╰╯╱╲▁▂▃▄▅▆▇█"
    width = 60
    
    print(f"\n{Colors.GREEN}", end='')
    start_time = time.time()
    
    while time.time() - start_time < duration:
        line = ''.join(random.choice(chars) for _ in range(width))
        print(line, end='\r', flush=True)
        time.sleep(0.1)
    
    print(f"{Colors.END}")

def main_animation():
    """Main animation sequence"""
    clear_screen()
    
    print(f"{Colors.BOLD}{Colors.CYAN}🎬 Starting Telegram Alias Bot...{Colors.END}\n")
    time.sleep(1)
    
    # Matrix intro effect
    matrix_effect(duration=1.5)
    
    # Main banner
    animate_banner()
    time.sleep(1)
    
    # Loading sequences
    progress_bar("Initializing bot system", 2)
    progress_bar("Loading configuration", 1.5)
    progress_bar("Connecting to Telegram", 2)
    progress_bar("Starting services", 1)
    
    # System info
    system_info()
    time.sleep(1)
    
    # Features showcase
    feature_showcase()
    time.sleep(1)
    
    # Commands preview
    commands_preview()
    time.sleep(1)
    
    # Final message
    print(f"\n{Colors.BOLD}{Colors.GREEN}🎉 Bot is ready! Starting main application...{Colors.END}\n")
    time.sleep(2)
    
    # Clear for main application
    clear_screen()

if __name__ == "__main__":
    main_animation()
