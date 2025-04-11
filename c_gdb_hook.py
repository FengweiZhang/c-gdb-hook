#!/usr/bin/env python3
"""
GDB Hook Script for RISC-V Debugging
This script provides enhanced debugging information with colored output and assembly code display.
"""

import gdb
import os
import shutil
import time
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum, auto

class TerminalColor(Enum):
    """Terminal color codes using ANSI escape sequences"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

@dataclass
class TerminalConfig:
    """Terminal configuration and capabilities"""
    width: int
    height: int
    has_color: bool

    @classmethod
    def get_current(cls) -> 'TerminalConfig':
        """Get current terminal configuration"""
        try:
            size = shutil.get_terminal_size()
            return cls(
                width=size.columns,
                height=size.lines,
                has_color=os.environ.get('TERM') == 'xterm-256color'
            )
        except Exception:
            return cls(width=80, height=24, has_color=False)

class TerminalFormatter:
    """Handles terminal output formatting with color support"""
    
    def __init__(self, config: TerminalConfig):
        self.config = config

    def colorize(self, text: str, color: TerminalColor) -> str:
        """Apply color to text if terminal supports it"""
        if self.config.has_color:
            return f"{color.value}{text}{TerminalColor.END.value}"
        return text

    def bold(self, text: str) -> str:
        """Make text bold if terminal supports it"""
        return self.colorize(text, TerminalColor.BOLD)

    def error(self, text: str) -> str:
        """Format error text"""
        return self.colorize(text, TerminalColor.RED)

    def success(self, text: str) -> str:
        """Format success text"""
        return self.colorize(text, TerminalColor.GREEN)

    def info(self, text: str) -> str:
        """Format info text"""
        return self.colorize(text, TerminalColor.CYAN)

    def warning(self, text: str) -> str:
        """Format warning text"""
        return self.colorize(text, TerminalColor.YELLOW)

    def white(self, text: str) -> str:
        """Format text in white"""
        return self.colorize(text, TerminalColor.WHITE)

    def blue(self, text: str) -> str:
        """Format text in blue"""
        return self.colorize(text, TerminalColor.BLUE)

    def red(self, text: str) -> str:
        """Format text in red"""
        return self.colorize(text, TerminalColor.RED)

class RegisterDisplay:
    """Handles register value display and formatting"""
    
    def __init__(self, formatter: TerminalFormatter):
        self.formatter = formatter
        self.registers = []

    def add_register(self, reg_name: str) -> bool:
        """Add a register to the display list"""
        try:
            # Verify the register exists by trying to read it
            gdb.parse_and_eval(f"${reg_name}")
            if reg_name not in self.registers:
                self.registers.append(reg_name)
                return True
            return False
        except gdb.error:
            return False

    def remove_register(self, reg_name: str) -> bool:
        """Remove a register from the display list"""
        if reg_name in self.registers:
            self.registers.remove(reg_name)
            return True
        return False

    def get_register_values(self) -> Dict[str, str]:
        """Get values of all tracked registers"""
        values = {}
        for reg in self.registers:
            try:
                value = gdb.parse_and_eval(f"${reg}")
                values[reg] = hex(value)
            except gdb.error:
                values[reg] = "Error"
        return values

    def format_output(self, values: Dict[str, str]) -> str:
        """Format register values for display"""
        width = self.formatter.config.width
        registers_per_line = max(1, width // 30)
        
        output = []
        current_line = []
        
        for reg_name, reg_value in values.items():
            # Format register name and value separately
            name_str = self.formatter.info(reg_name)
            value_str = self.formatter.success(reg_value)
            
            # Calculate padding for alignment
            name_pad = 8 - len(reg_name)  # Account for actual text length
            value_pad = 12 - len(reg_value)  # Account for actual text length
            
            # Create the formatted string with proper padding
            reg_str = (
                f"{name_str}{' ' * name_pad} = "
                f"{value_str}{' ' * value_pad}"
            )
            current_line.append(reg_str)
            
            if len(current_line) >= registers_per_line:
                output.append(" | ".join(current_line))
                current_line = []
        
        if current_line:
            output.append(" | ".join(current_line))
        
        return "\n".join(output)

    def display(self) -> None:
        """Display register values"""
        print(f"\n{self.formatter.bold('Registers:')}")
        values = self.get_register_values()
        print(self.format_output(values))

class AssemblyDisplay:
    """Handles assembly code display and formatting"""
    
    def __init__(self, formatter: TerminalFormatter):
        self.formatter = formatter
        self.instructions_before = 5
        self.instructions_after = 10

    def get_assembly_range(self, pc: int) -> Tuple[int, int]:
        """Calculate address range for assembly display"""
        start = pc - self.instructions_before * 4
        end = pc + self.instructions_after * 4
        return start, end

    def display(self) -> None:
        """Display assembly code around current PC"""
        try:
            frame = gdb.selected_frame()
            pc = frame.pc()
            start_addr, end_addr = self.get_assembly_range(pc)
            
            print(f"\n{self.formatter.bold('Assembly Code:')}")
            print("-" * self.formatter.config.width)
            
            # Use GDB's native x/i command with range and preserve color
            cmd = f"x/{self.instructions_before + self.instructions_after + 1}i {start_addr}"
            gdb.execute(cmd, to_string=False)  # This will print directly with GDB's colors
            
        except gdb.error as e:
            print(self.formatter.error(f"\nError reading assembly code: {e}"))

class BacktraceDisplay:
    """Handles backtrace display and formatting"""
    
    def __init__(self, formatter: TerminalFormatter):
        self.formatter = formatter
        self.max_frames = 10  # Maximum number of frames to display

    def display(self) -> None:
        """Display the backtrace using GDB's native format"""
        try:
            print(f"\n{self.formatter.bold('Backtrace:')}")
            print("-" * self.formatter.config.width)
            
            # Use GDB's native bt command and preserve color
            gdb.execute(f"bt {self.max_frames}", to_string=False)  # This will print directly with GDB's colors
            
        except gdb.error as e:
            print(self.formatter.error(f"\nError reading backtrace: {e}"))

class SourceDisplay:
    """Handles source code display and formatting"""
    
    def __init__(self, formatter: TerminalFormatter):
        self.formatter = formatter
        self.lines_before = 5
        self.lines_after = 10

    def display(self) -> None:
        """Display source code around current line"""
        try:
            frame = gdb.selected_frame()
            sal = frame.find_sal()
            
            if not sal or not sal.symtab:
                print(self.formatter.error("No source information available"))
                return
                
            print(f"\n{self.formatter.bold('Source Code:')}")
            print("-" * self.formatter.config.width)
            
            # Get current file and line
            file_name = os.path.basename(sal.symtab.filename)
            current_line = sal.line
            
            # Calculate line range
            start_line = max(1, current_line - self.lines_before)
            end_line = current_line + self.lines_after
            
            # Read source lines
            with open(sal.symtab.filename, 'r') as f:
                lines = f.readlines()
            
            # Display source lines
            for i in range(start_line - 1, min(end_line, len(lines))):
                line_num = i + 1
                line = lines[i].rstrip()
                
                # Format line number and content
                if line_num == current_line:
                    # Current line - highlight it
                    print(self.formatter.white(f"{line_num:>4} => {line}"))
                else:
                    print(f"{line_num:>4}    {line}")
                    
        except Exception as e:
            print(self.formatter.error(f"Error reading source code: {e}"))

class VariableDisplay:
    """Handles variable value display and formatting"""
    
    def __init__(self, formatter: TerminalFormatter):
        self.formatter = formatter
        self.variables = []  # List of variables to track

    def add_variable(self, var_name: str) -> bool:
        """Add a variable to the display list"""
        try:
            # Verify the variable exists by trying to read it
            gdb.parse_and_eval(var_name)
            if var_name not in self.variables:
                self.variables.append(var_name)
                return True
            return False
        except gdb.error:
            return False

    def remove_variable(self, var_name: str) -> bool:
        """Remove a variable from the display list"""
        if var_name in self.variables:
            self.variables.remove(var_name)
            return True
        return False

    def display(self) -> None:
        """Display variable values using GDB's native format"""
        if not self.variables:
            return
            
        print(f"\n{self.formatter.bold('Variables:')}")
        print("-" * self.formatter.config.width)
        
        for var in self.variables:
            # Print variable header
            print(self.formatter.bold(f"Variable {self.formatter.blue(var)}:"))
            
            # Use GDB's native print command and preserve color
            cmd = f"print {var}"
            gdb.execute(cmd, to_string=False)  # This will print directly with GDB's colors

class MemoryBlock:
    """Represents a block of memory to track"""
    def __init__(self, start_addr: int, size: int):
        self.start_addr = start_addr
        self.size = size
        self.end_addr = start_addr + size

class MemoryDisplay:
    """Handles memory block display and formatting"""
    
    def __init__(self, formatter: TerminalFormatter):
        self.formatter = formatter
        self.memory_blocks = []  # List of MemoryBlock objects

    def add_memory_block(self, start_addr: int, size: int) -> bool:
        """Add a memory block to track"""
        try:
            # Verify the memory range is valid by trying to read it
            gdb.parse_and_eval(f"*(unsigned char*){start_addr}")
            gdb.parse_and_eval(f"*(unsigned char*){start_addr + size - 1}")
            
            # Check for overlapping blocks
            new_block = MemoryBlock(start_addr, size)
            for block in self.memory_blocks:
                if (new_block.start_addr <= block.end_addr and 
                    new_block.end_addr >= block.start_addr):
                    return False
            
            self.memory_blocks.append(new_block)
            return True
        except gdb.error:
            return False

    def remove_memory_block(self, addr: int) -> bool:
        """Remove a memory block by its start address"""
        for block in self.memory_blocks:
            if block.start_addr == addr:
                self.memory_blocks.remove(block)
                return True
        return False

    def display(self) -> None:
        """Display memory values using GDB's native format"""
        if not self.memory_blocks:
            return

        print(f"\n{self.formatter.bold('Memory Blocks:')}")
        print("-" * self.formatter.config.width)
        
        for block in self.memory_blocks:
            # Print block header
            print(self.formatter.bold(f"Memory Block at {self.formatter.blue(f'0x{block.start_addr:08x}')}:"))
            
            # Calculate number of lines needed (4 words per line)
            words = block.size // 4
            lines = (words + 3) // 4  # Round up to nearest 4 words
            
            # Use GDB's x command to display memory in hex format
            for i in range(lines):
                addr = block.start_addr + (i * 16)  # 16 bytes (4 words) per line
                if addr < block.end_addr:
                    # Use GDB's native x command with 4 words and preserve color
                    cmd = f"x/4wx {addr}"
                    gdb.execute(cmd, to_string=False)  # This will print directly with GDB's colors
            
            # Add separator between blocks
            print("-" * self.formatter.config.width)

class CommandDisplay:
    """Handles custom GDB command display and execution"""
    
    def __init__(self, formatter: TerminalFormatter):
        self.formatter = formatter
        self.commands = []  # List of commands

    def add_command(self, command: str) -> bool:
        """Add a custom command to the display list"""
        try:
            # Don't varify
            # gdb.execute(command, to_string=True)
            if command not in self.commands:
                self.commands.append(command)
                return True
            return False
        except gdb.error:
            return False

    def remove_command(self, index: int) -> bool:
        """Remove a command from the display list by index"""
        try:
            if 0 <= index < len(self.commands):
                self.commands.pop(index)
                return True
            return False
        except (ValueError, IndexError):
            return False

    def display(self) -> None:
        """Display and execute custom commands"""
        if not self.commands:
            return
            
        print(f"\n{self.formatter.bold('Custom Commands:')}")
        print("-" * self.formatter.config.width)
        
        for i, command in enumerate(self.commands):
            # Print command header with index
            print(self.formatter.bold(f"Command {self.formatter.blue(f'#{i}')}:"))
            
            # Execute the command and preserve color
            gdb.execute(command, to_string=False)

class DisplaySettings:
    """Manages display settings for debug output"""
    
    def __init__(self):
        self.show_registers = False
        self.show_backtrace = False
        self.show_assembly = False
        self.show_source = False
        self.show_variables = False
        self.show_memory = False
        self.show_commands = False
        self.show_thread_id = True  # Keep this setting
        # Header information settings
        self.show_display_settings = False
        self.show_display_order = False
        # Define display order (0 is first, higher numbers are later)
        self.display_order = {
            "thread": 0,
            "backtrace": 1,
            "memory": 2,
            "source": 3,
            "assembly": 4,
            "registers": 5,
            "variables": 6,
            "commands": 7,
        }

    def toggle_registers(self) -> None:
        """Toggle register display"""
        self.show_registers = not self.show_registers

    def toggle_backtrace(self) -> None:
        """Toggle backtrace display"""
        self.show_backtrace = not self.show_backtrace

    def toggle_assembly(self) -> None:
        """Toggle assembly display"""
        self.show_assembly = not self.show_assembly

    def toggle_source(self) -> None:
        """Toggle source display"""
        self.show_source = not self.show_source

    def toggle_variables(self) -> None:
        """Toggle variable display"""
        self.show_variables = not self.show_variables

    def toggle_memory(self) -> None:
        """Toggle memory display"""
        self.show_memory = not self.show_memory

    def toggle_commands(self) -> None:
        """Toggle custom commands display"""
        self.show_commands = not self.show_commands

    def get_status(self) -> str:
        """Get current display status"""
        status = []
        status.append(f"Thread ID: {'on' if self.show_thread_id else 'off'}")
        status.append(f"Registers: {'on' if self.show_registers else 'off'}")
        status.append(f"Backtrace: {'on' if self.show_backtrace else 'off'}")
        status.append(f"Assembly: {'on' if self.show_assembly else 'off'}")
        status.append(f"Source: {'on' if self.show_source else 'off'}")
        status.append(f"Variables: {'on' if self.show_variables else 'off'}")
        status.append(f"Memory: {'on' if self.show_memory else 'off'}")
        status.append(f"Commands: {'on' if self.show_commands else 'off'}")
        return " | ".join(status)

    def get_display_order(self) -> str:
        """Get current display order"""
        # Sort items by their order value
        sorted_items = sorted(self.display_order.items(), key=lambda x: x[1])
        return " -> ".join(item[0] for item in sorted_items)

    def reorder_display(self, new_order: str) -> bool:
        """Change the display order of blocks"""
        try:
            # Split the new order string into a list
            blocks = [block.strip().lower() for block in new_order.split(",")]
            
            # Validate all blocks are present
            if set(blocks) != set(self.display_order.keys()):
                return False
                
            # Update the order
            for i, block in enumerate(blocks):
                self.display_order[block] = i
                
            return True
        except:
            return False

class ThreadDisplay:
    """Handles thread information display"""
    
    def __init__(self, formatter: TerminalFormatter):
        self.formatter = formatter

    def display(self) -> None:
        """Display thread information"""
        try:
            thread = gdb.selected_thread()
            thread_id = thread.num
            print(
                self.formatter.bold("Thread ID: ") +
                self.formatter.info(str(thread_id))
            )
        except Exception as e:
            print(self.formatter.error(f"Error getting thread information: {e}"))

class DebugDisplay:
    """Main class for handling debug information display"""
    
    def __init__(self):
        self.config = TerminalConfig.get_current()
        self.formatter = TerminalFormatter(self.config)
        self.thread_display = ThreadDisplay(self.formatter)
        self.register_display = RegisterDisplay(self.formatter)
        self.assembly_display = AssemblyDisplay(self.formatter)
        self.backtrace_display = BacktraceDisplay(self.formatter)
        self.source_display = SourceDisplay(self.formatter)
        self.variable_display = VariableDisplay(self.formatter)
        self.memory_display = MemoryDisplay(self.formatter)
        self.command_display = CommandDisplay(self.formatter)
        self.settings = DisplaySettings()

    def display(self) -> None:
        """Display all debug information"""
        try:
            # Display current settings if enabled
            if self.settings.show_display_settings:
                print(
                    self.formatter.bold("Display Settings: ") +
                    self.formatter.info(self.settings.get_status())
                )

            # Display order if enabled
            if self.settings.show_display_order:
                print(
                    self.formatter.bold("Display Order: ") +
                    self.formatter.info(self.settings.get_display_order())
                )

            if any([self.settings.show_display_settings, 
                   self.settings.show_display_order]):
                print("-" * self.formatter.config.width)

            # Create a list of display functions with their conditions and names
            display_functions = [
                (self.settings.show_thread_id, self.thread_display.display, "thread"),
                (self.settings.show_backtrace, self.backtrace_display.display, "backtrace"),
                (self.settings.show_source, self.source_display.display, "source"),
                (self.settings.show_registers, self.register_display.display, "registers"),
                (self.settings.show_variables, self.variable_display.display, "variables"),
                (self.settings.show_memory, self.memory_display.display, "memory"),
                (self.settings.show_assembly, self.assembly_display.display, "assembly"),
                (self.settings.show_commands, self.command_display.display, "commands")
            ]

            # Sort display functions based on current order
            sorted_functions = sorted(
                display_functions,
                key=lambda x: self.settings.display_order[x[2]]
            )

            # Execute display functions in order
            for condition, func, _ in sorted_functions:
                if condition:
                    func()
                    print("-" * self.formatter.config.width)

        except Exception as e:
            print(self.formatter.error(f"Error in debug display: {e}"))

# Global debug display instance
debug_display = DebugDisplay()

class ToggleRegistersCommand(gdb.Command):
    """Command to toggle register display"""
    
    def __init__(self):
        super(ToggleRegistersCommand, self).__init__("c-toggle-registers", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.toggle_registers()
        print(debug_display.formatter.success(f"Register display {'enabled' if debug_display.settings.show_registers else 'disabled'}"))

class ToggleBacktraceCommand(gdb.Command):
    """Command to toggle backtrace display"""
    
    def __init__(self):
        super(ToggleBacktraceCommand, self).__init__("c-toggle-backtrace", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.toggle_backtrace()
        print(debug_display.formatter.success(f"Backtrace display {'enabled' if debug_display.settings.show_backtrace else 'disabled'}"))

class ToggleAssemblyCommand(gdb.Command):
    """Command to toggle assembly display"""
    
    def __init__(self):
        super(ToggleAssemblyCommand, self).__init__("c-toggle-assembly", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.toggle_assembly()
        print(debug_display.formatter.success(f"Assembly display {'enabled' if debug_display.settings.show_assembly else 'disabled'}"))

class ToggleSourceCommand(gdb.Command):
    """Command to toggle source display"""
    
    def __init__(self):
        super(ToggleSourceCommand, self).__init__("c-toggle-source", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.toggle_source()
        print(debug_display.formatter.success(f"Source display {'enabled' if debug_display.settings.show_source else 'disabled'}"))

class ToggleVariablesCommand(gdb.Command):
    """Command to toggle variable display"""
    
    def __init__(self):
        super(ToggleVariablesCommand, self).__init__("c-toggle-variables", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.toggle_variables()
        print(debug_display.formatter.success(f"Variable display {'enabled' if debug_display.settings.show_variables else 'disabled'}"))

class ToggleMemoryCommand(gdb.Command):
    """Command to toggle memory display"""
    
    def __init__(self):
        super(ToggleMemoryCommand, self).__init__("c-toggle-memory", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.toggle_memory()
        print(debug_display.formatter.success(f"Memory display {'enabled' if debug_display.settings.show_memory else 'disabled'}"))

class ToggleCommandsCommand(gdb.Command):
    """Command to toggle custom commands display"""
    
    def __init__(self):
        super(ToggleCommandsCommand, self).__init__("c-toggle-commands", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.toggle_commands()
        print(debug_display.formatter.success(f"Custom commands display {'enabled' if debug_display.settings.show_commands else 'disabled'}"))

class AddRegisterCommand(gdb.Command):
    """Command to add registers to the display list"""
    
    def __init__(self):
        super(AddRegisterCommand, self).__init__("c-add-register", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not arg:
            print(debug_display.formatter.error("Please specify register names separated by spaces"))
            print(debug_display.formatter.info("Example: c-add-register ra sp gp tp"))
            return
            
        # Split registers by spaces and filter out empty strings
        reg_names = [reg for reg in arg.split() if reg.strip()]
        
        # Track success and failure counts
        success_count = 0
        failed_regs = []
        
        for reg_name in reg_names:
            if debug_display.register_display.add_register(reg_name):
                success_count += 1
                debug_display.settings.show_registers = True
            else:
                failed_regs.append(reg_name)
        
        # Print summary
        if success_count > 0:
            print(debug_display.formatter.success(f"Added {success_count} register(s) to display list"))
        if failed_regs:
            print(debug_display.formatter.error(f"Failed to add register(s): {' '.join(failed_regs)}"))
        if debug_display.register_display.registers:
            debug_display.settings.show_registers = True

class RemoveRegisterCommand(gdb.Command):
    """Command to remove a register from the display list"""
    
    def __init__(self):
        super(RemoveRegisterCommand, self).__init__("c-rm-register", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not arg:
            print(debug_display.formatter.error("Please specify a register name"))
            return
            
        reg_names = [reg for reg in arg.split() if reg.strip()]

        success_count = 0
        failed_regs = []

        for reg_name in reg_names:
            if debug_display.register_display.remove_register(reg_name):
                success_count += 1
            else:
                failed_regs.append(reg_name)

        if success_count > 0:
            print(debug_display.formatter.success(f"Removed {success_count} register(s) from display list"))
        if failed_regs:
            print(debug_display.formatter.error(f"Failed to remove register(s): {' '.join(failed_regs)}"))
        if not debug_display.register_display.registers:
            debug_display.settings.show_registers = False

class AddVariableCommand(gdb.Command):
    """Command to add a variable to the display list"""
    
    def __init__(self):
        super(AddVariableCommand, self).__init__("c-add-variable", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not arg:
            print(debug_display.formatter.error("Please specify a variable name"))
            return
            
        var_names = [var for var in arg.split() if var.strip()]

        success_count = 0
        failed_vars = []

        for var_name in var_names:
            if debug_display.variable_display.add_variable(var_name):
                success_count += 1
            else:
                failed_vars.append(var_name)

        if success_count > 0:
            print(debug_display.formatter.success(f"Added {success_count} variable(s) to display list"))
        if failed_vars:
            print(debug_display.formatter.error(f"Failed to add variable(s): {' '.join(failed_vars)}"))
        if debug_display.variable_display.variables:
            debug_display.settings.show_variables = True

class RemoveVariableCommand(gdb.Command):
    """Command to remove a variable from the display list"""
    
    def __init__(self):
        super(RemoveVariableCommand, self).__init__("c-rm-variable", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not arg:
            print(debug_display.formatter.error("Please specify a variable name"))
            return
            
        var_names = [var for var in arg.split() if var.strip()]

        success_count = 0
        failed_vars = []

        for var_name in var_names:
            if debug_display.variable_display.remove_variable(var_name):
                success_count += 1
            else:
                failed_vars.append(var_name)

        if success_count > 0:
            print(debug_display.formatter.success(f"Removed {success_count} variable(s) from display list"))
        if failed_vars:
            print(debug_display.formatter.error(f"Failed to add variable(s): {' '.join(failed_vars)}"))
        if not debug_display.variable_display.variables:
            debug_display.settings.show_variables = False

class AddMemoryBlockCommand(gdb.Command):
    """Command to add a memory block to track"""
    
    def __init__(self):
        super(AddMemoryBlockCommand, self).__init__("c-add-memory", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not arg:
            print(debug_display.formatter.error("Please specify start address and size"))
            print(debug_display.formatter.info("Example: c-add-memory 0x80000000 1024"))
            return
            
        try:
            start_addr, size = arg.split()
            start_addr = int(start_addr, 16) if start_addr.startswith("0x") else int(start_addr)
            size = int(size, 16) if size.startswith("0x") else int(size)
            
            if debug_display.memory_display.add_memory_block(start_addr, size):
                debug_display.settings.show_memory = True
                print(debug_display.formatter.success(f"Added memory block at 0x{start_addr:08x} with size {size}"))
            else:
                print(debug_display.formatter.error(f"Failed to add memory block at 0x{start_addr:08x}"))
        except ValueError:
            print(debug_display.formatter.error("Invalid arguments. Use: c-add-memory <start_addr> <size>"))

class RemoveMemoryBlockCommand(gdb.Command):
    """Command to remove a memory block by its start address"""
    
    def __init__(self):
        super(RemoveMemoryBlockCommand, self).__init__("c-rm-memory", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not arg:
            print(debug_display.formatter.error("Please specify the start address of the memory block to remove"))
            print(debug_display.formatter.info("Example: c-rm-memory 0x80000000"))
            return
            
        try:
            addr = int(arg, 16) if arg.startswith("0x") else int(arg)
            if debug_display.memory_display.remove_memory_block(addr):
                print(debug_display.formatter.success(f"Removed memory block at 0x{addr:08x}"))
            else:
                print(debug_display.formatter.error(f"No memory block found at 0x{addr:08x}"))
        except ValueError:
            print(debug_display.formatter.error("Invalid address. Use: c-rm-memory <start_addr>"))

class ReorderDisplayCommand(gdb.Command):
    """Command to change the display order of debug blocks"""
    
    def __init__(self):
        super(ReorderDisplayCommand, self).__init__("c-reorder", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not arg:
            print(debug_display.formatter.error("Please specify the new order"))
            print(debug_display.formatter.info("Example: c-reorder backtrace,source,registers,variables,memory,assembly,commands"))
            return
            
        new_order = arg.strip()
        if debug_display.settings.reorder_display(new_order):
            print(debug_display.formatter.success("Display order updated successfully"))
            print(debug_display.formatter.info(f"New order: {debug_display.settings.get_display_order()}"))
        else:
            print(debug_display.formatter.error("Invalid order. Use: backtrace,source,registers,variables,memory,assembly,commands"))

class ClearScreenCommand(gdb.Command):
    """Command to clear the GDB screen"""
    
    def __init__(self):
        super(ClearScreenCommand, self).__init__("c-clear", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        # Use GDB's shell command to clear the screen
        gdb.execute("shell clear", to_string=False)

class ShowDebugCommand(gdb.Command):
    """Command to show debug information"""
    
    def __init__(self):
        super(ShowDebugCommand, self).__init__("c-show", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        # Clear screen first if requested
        if arg and arg.strip() == "clear":
            gdb.execute("shell clear", to_string=False)
        
        # Display debug information
        debug_display.display()

class CustomHelpCommand(gdb.Command):
    """Command to display help information for all custom commands"""
    
    def __init__(self):
        super(CustomHelpCommand, self).__init__("c-help", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        help_text = [
            debug_display.formatter.bold("GDB Custom Debug Info Commands Help"),
            debug_display.formatter.bold("=" * 50),
            "",
            debug_display.formatter.info("Debug Information Management"),
            debug_display.formatter.bold("-" * 20),
            "Register Management:",
            "  c-add-register <reg>    - Add register to display list",
            "  c-rm-register <reg>     - Remove register from display list",
            "",
            "Variable Management:",
            "  c-add-variable <var>    - Add variable to display list",
            "  c-rm-variable <var>     - Remove variable from display list",
            "",
            "Memory Management:",
            "  c-add-memory <addr> <size>    - Add memory block to track",
            "  c-rm-memory <addr>            - Remove memory block by start address",
            "",
            "Command Management:",
            "  c-add-command <cmd>     - Add GDB command to display list",
            "  c-rm-command <index>    - Remove command by its index",
            "",
            debug_display.formatter.info("Display Control"),
            debug_display.formatter.bold("-" * 20),
            "Display Toggle Commands:",
            "  c-toggle-*  - Toggle [thread,registers,backtrace,assembly,source,variable,memory,commands] display",
            "",
            "Display Enable/Disable Commands:",
            "  c-enable-*  - Enable [thread,registers,backtrace,assembly,source,variable,memory,commands] display",
            "  c-disable-* - Disable [thread,registers,backtrace,assembly,source,variable,memory,commands] display",
            "",
            "Header Information Control:",
            "  c-enable-display-settings  - Enable display settings information",
            "  c-disable-display-settings - Disable display settings information",
            "  c-enable-display-order     - Enable display order information",
            "  c-disable-display-order    - Disable display order information",
            "",
            "Display Management:",
            "  c-show [clear]     - Show debug information (with optional screen clear)",
            "  c-clear            - Clear the screen",
            "  c-reorder <order>  - Change display order (e.g., thread,backtrace,source,registers,variables,memory,assembly,commands)",
            "",
            debug_display.formatter.info("Setting Management"),
            debug_display.formatter.bold("-" * 20),
            "  c-set <setting> <value> - Set a specific setting, c-set help for more information",
            "",
            debug_display.formatter.info("Current Settings Status"),
            debug_display.formatter.bold("-" * 20),
            "Display Settings:",
            debug_display.formatter.info(debug_display.settings.get_status()),
            "Display Order:",
            debug_display.formatter.info(debug_display.settings.get_display_order()),
            "",
            debug_display.formatter.info("Help"),
            debug_display.formatter.bold("-" * 20),
            "  c-help    - Show this help message",
            "",
            debug_display.formatter.info("Note: All commands start with 'c-' prefix")
        ]
        print("\n".join(help_text))

class SetCommand(gdb.Command):
    """Command to configure debug display settings"""
    
    def __init__(self):
        super(SetCommand, self).__init__("c-set", gdb.COMMAND_USER)

    def set_display_settings(self, item_list: str, value: bool):
        blocks = [block.strip().lower() for block in item_list.split(",")]
        success_list = []
        for item in blocks:
            if item == "thread":
                debug_display.settings.show_thread_id = value
                success_list.append(item)
            elif item == "backtrace":
                debug_display.settings.show_backtrace = value
                success_list.append(item)
            elif item == "source":
                debug_display.settings.show_source = value
                success_list.append(item)
            elif item == "registers":
                debug_display.settings.show_registers = value
                success_list.append(item)
            elif item == "variables":
                debug_display.settings.show_variables = value
                success_list.append(item)
            elif item == "memory":
                debug_display.settings.show_memory = value
                success_list.append(item)
            elif item == "assembly":
                debug_display.settings.show_assembly = value
                success_list.append(item)
            elif item == "commands":
                debug_display.settings.show_commands = value
                success_list.append(item)
        if success_list:
            print(debug_display.formatter.success(f"Display settings updated: {', '.join(success_list)}"))
        else:
            print(debug_display.formatter.error("Invalid display settings"))


    def invoke(self, arg, from_tty):
        if not arg:
            print(debug_display.formatter.error("Please specify a setting to configure"))
            print(debug_display.formatter.info("Available settings:"))
            print(debug_display.formatter.info("  [enable|disable] <list>   - Show/hide display (e.g., thread,backtrace,source,registers,variables,memory,assembly,commands)"))
            print(debug_display.formatter.info("  order <list>              - Set display order (e.g., thread,backtrace,source,registers,variables,memory,assembly,commands)"))
            print(debug_display.formatter.info("  source-line <start> <end> - Set source line range (e.g., c-set source-line -5 10)"))
            return

        args = arg.split()
        setting = args[0].lower()

        if setting == "enable":
            value = args[1].lower() if len(args) > 1 else None
            if not value:
                print(debug_display.formatter.error("Please specify the list of items to enable"))
                print(debug_display.formatter.info("Example: c-set enable thread,backtrace,source,registers,variables,memory,assembly,commands"))
                return
            self.set_display_settings(value, True)
        elif setting == "disable":
            value = args[1].lower() if len(args) > 1 else None
            if not value:
                print(debug_display.formatter.error("Please specify the list of items to disable"))
                print(debug_display.formatter.info("Example: c-set disable thread,backtrace,source,registers,variables,memory,assembly,commands"))
                return
            self.set_display_settings(value, False)
        elif setting == "order":
            value = args[1].lower() if len(args) > 1 else None
            if not value:
                print(debug_display.formatter.error("Please specify the new display order"))
                print(debug_display.formatter.info("Example: c-set order thread,backtrace,source,registers,variables,memory,assembly,commands"))
                return
            if debug_display.settings.reorder_display(value):
                print(debug_display.formatter.success("Display order updated successfully"))
                print(debug_display.formatter.info(f"New order: {debug_display.settings.get_display_order()}"))
            else:
                print(debug_display.formatter.error("Invalid order. Use: thread,backtrace,source,registers,variables,memory,assembly,commands"))
        elif setting == "source-line":
            try:
                start = int(args[1]) if len(args) > 2 else None
                end = int(args[2]) if len(args) > 2 else None
            except Exception as e:
                print(debug_display.formatter.error("Please specify the source line range to set"))
                print(debug_display.formatter.info("Example: c-set source-line -5 10"))
                return
            debug_display.source_display.lines_before = -start
            debug_display.source_display.lines_after = end
        else:
            print(debug_display.formatter.error(f"Unknown setting: {setting}"))
            print(debug_display.formatter.info("Available settings: display-settings, display-order, order"))

class AddCommandCommand(gdb.Command):
    """Command to add a custom GDB command to display"""
    
    def __init__(self):
        super(AddCommandCommand, self).__init__("c-add-command", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not arg:
            print(debug_display.formatter.error("Please specify the GDB command to add"))
            print(debug_display.formatter.info("Example: c-add-command info registers"))
            return
            
        command = arg.strip()
        if debug_display.command_display.add_command(command):
            index = len(debug_display.command_display.commands) - 1
            debug_display.settings.show_commands = True
            print(debug_display.formatter.success(f"Added command #{index} to display list"))
        else:
            print(debug_display.formatter.error(f"Failed to add command"))

class RemoveCommandCommand(gdb.Command):
    """Command to remove a custom command from display"""
    
    def __init__(self):
        super(RemoveCommandCommand, self).__init__("c-rm-command", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not arg:
            print(debug_display.formatter.error("Please specify the command index to remove"))
            print(debug_display.formatter.info("Example: c-rm-command 0"))
            return
            
        try:
            index = int(arg)
            if debug_display.command_display.remove_command(index):
                print(debug_display.formatter.success(f"Removed command #{index} from display list"))
            else:
                print(debug_display.formatter.error(f"Command #{index} not found in display list"))
        except ValueError:
            print(debug_display.formatter.error("Invalid index. Use: c-rm-command <index>"))

# Add new enable/disable commands
class EnableRegistersCommand(gdb.Command):
    """Command to enable register display"""
    
    def __init__(self):
        super(EnableRegistersCommand, self).__init__("c-enable-registers", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.show_registers = True
        print(debug_display.formatter.success("Register display enabled"))

class DisableRegistersCommand(gdb.Command):
    """Command to disable register display"""
    
    def __init__(self):
        super(DisableRegistersCommand, self).__init__("c-disable-registers", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.show_registers = False
        print(debug_display.formatter.success("Register display disabled"))

class EnableBacktraceCommand(gdb.Command):
    """Command to enable backtrace display"""
    
    def __init__(self):
        super(EnableBacktraceCommand, self).__init__("c-enable-backtrace", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.show_backtrace = True
        print(debug_display.formatter.success("Backtrace display enabled"))

class DisableBacktraceCommand(gdb.Command):
    """Command to disable backtrace display"""
    
    def __init__(self):
        super(DisableBacktraceCommand, self).__init__("c-disable-backtrace", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.show_backtrace = False
        print(debug_display.formatter.success("Backtrace display disabled"))

class EnableAssemblyCommand(gdb.Command):
    """Command to enable assembly display"""
    
    def __init__(self):
        super(EnableAssemblyCommand, self).__init__("c-enable-assembly", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.show_assembly = True
        print(debug_display.formatter.success("Assembly display enabled"))

class DisableAssemblyCommand(gdb.Command):
    """Command to disable assembly display"""
    
    def __init__(self):
        super(DisableAssemblyCommand, self).__init__("c-disable-assembly", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.show_assembly = False
        print(debug_display.formatter.success("Assembly display disabled"))

class EnableSourceCommand(gdb.Command):
    """Command to enable source display"""
    
    def __init__(self):
        super(EnableSourceCommand, self).__init__("c-enable-source", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.show_source = True
        print(debug_display.formatter.success("Source display enabled"))

class DisableSourceCommand(gdb.Command):
    """Command to disable source display"""
    
    def __init__(self):
        super(DisableSourceCommand, self).__init__("c-disable-source", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.show_source = False
        print(debug_display.formatter.success("Source display disabled"))

class EnableVariablesCommand(gdb.Command):
    """Command to enable variable display"""
    
    def __init__(self):
        super(EnableVariablesCommand, self).__init__("c-enable-variables", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.show_variables = True
        print(debug_display.formatter.success("Variable display enabled"))

class DisableVariablesCommand(gdb.Command):
    """Command to disable variable display"""
    
    def __init__(self):
        super(DisableVariablesCommand, self).__init__("c-disable-variables", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.show_variables = False
        print(debug_display.formatter.success("Variable display disabled"))

class EnableMemoryCommand(gdb.Command):
    """Command to enable memory display"""
    
    def __init__(self):
        super(EnableMemoryCommand, self).__init__("c-enable-memory", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.show_memory = True
        print(debug_display.formatter.success("Memory display enabled"))

class DisableMemoryCommand(gdb.Command):
    """Command to disable memory display"""
    
    def __init__(self):
        super(DisableMemoryCommand, self).__init__("c-disable-memory", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.show_memory = False
        print(debug_display.formatter.success("Memory display disabled"))

class EnableCommandsCommand(gdb.Command):
    """Command to enable custom commands display"""
    
    def __init__(self):
        super(EnableCommandsCommand, self).__init__("c-enable-commands", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.show_commands = True
        print(debug_display.formatter.success("Custom commands display enabled"))

class DisableCommandsCommand(gdb.Command):
    """Command to disable custom commands display"""
    
    def __init__(self):
        super(DisableCommandsCommand, self).__init__("c-disable-commands", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        debug_display.settings.show_commands = False
        print(debug_display.formatter.success("Custom commands display disabled"))


# Register GDB commands
EnableRegistersCommand()
DisableRegistersCommand()
ToggleRegistersCommand()
EnableBacktraceCommand()
DisableBacktraceCommand()
ToggleBacktraceCommand()
EnableAssemblyCommand()
DisableAssemblyCommand()
ToggleAssemblyCommand()
EnableSourceCommand()
DisableSourceCommand()
ToggleSourceCommand()
EnableVariablesCommand()
DisableVariablesCommand()
ToggleVariablesCommand()
EnableMemoryCommand()
DisableMemoryCommand()
ToggleMemoryCommand()
EnableCommandsCommand()
DisableCommandsCommand()
ToggleCommandsCommand()

AddRegisterCommand()
RemoveRegisterCommand()
AddVariableCommand()
RemoveVariableCommand()
AddMemoryBlockCommand()
RemoveMemoryBlockCommand()
AddCommandCommand()
RemoveCommandCommand()

ShowDebugCommand()
ClearScreenCommand()
ReorderDisplayCommand()
CustomHelpCommand()
SetCommand()

def start_handler(event):
    """Handler for program start"""
    print(debug_display.formatter.success("Program started"))
    debug_display.display()

def stop_handler(event):
    """Handler for program stop"""
    debug_display.display()

def continue_handler(event):
    """Handler for program continue"""
    print(debug_display.formatter.success("Program continued"))
    debug_display.display()

# Register event handlers
gdb.events.stop.connect(stop_handler)
#gdb.events.cont.connect(continue_handler)
#gdb.events.exited.connect(stop_handler)
#gdb.events.new_objfile.connect(start_handler)


