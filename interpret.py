#!/usr/bin/env python3


# Libraries
import sys
import xml.etree.ElementTree as ET
import re
import logging


# === Constants ===
ERROR_IDK = 420
ERROR_ARGUMENT = 10
ERROR_FILE = 11
ERROR_STRUCTURE = 31
ERROR_SYNTAX = 32
ERROR_SEMANTIC = 52
ERROR_OPERANDS = 53
ERROR_NOTEXISTVARIABLE = 54
ERROR_NOTEXISTSCOPE = 55
ERROR_MISSINGVALUE = 56
ERROR_ZERODIVIDE = 57
ERROR_STRING = 58


# === Debug logs ===
logger = logging.getLogger("interpret")
handler = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s:%(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel("DEBUG")


# === Main function ===
def main():
	filePath = processProgramArguments()

	logger.debug("==================================\nfile: {0}\n==============================\n".format(filePath))
	
	# --- Opening input file ---
	try:
		tree = ET.ElementTree(file=filePath)	# @todo Throws error when no root found
	except IOError:
		print("Opening input file error", file=sys.stderr)
		sys.exit(ERROR_FILE)		


	# --- Checking root node ---
	root = tree.getroot()
	# @todo check if root not found???
	if root.tag != "program":
		sys.exit(ERROR_IDK)
	if "language" in root.attrib:
		if root.attrib["language"] != "IPPcode18":	# @todo Case sensitive or not?
			sys.exit(ERROR_IDK)	# Invalid language
		del root.attrib["language"]
	else:
		sys.exit(ERROR_IDK)	# Language missing
	if "name" in root.attrib:
		del root.attrib["name"]
	if "description" in root.attrib:
		del root.attrib["description"]
	if len(root.attrib) != 0:
		sys.exit(ERROR_IDK)	# Attributes error
		
		
	# --- Processing instructions ---
	global interpret
	interpret = Interpret()
	interpret.loadInstructions(root)
		
		
# === Other functions ===
def errorExit(code, msg):
	print("ERROR: {0}".format(msg), file=sys.stderr)
	sys.exit(code)	


def processProgramArguments(): # @todo space in source name
	if len(sys.argv) != 2:
		print("Invalid argument count", file=sys.stderr)
		sys.exit(ERROR_ARGUMENT)
	
	if sys.argv[1] == "--help":
		print("@todo")
		sys.exit(0)
	elif sys.argv[1][:9] == "--source=":
		return sys.argv[1][9:]	
	else:
		print("Illegal argument", file=sys.stderr)
		sys.exit(ERROR_ARGUMENT)
		
		
# === Classes ===		
class Frames:
	globalFrame = {}
	localFrame = None
	temporaryFrame = None
	stack = []
	
	@classmethod
	def add(cls, name):
		# --- Identify frame ---
		frame = cls.__identifyFrame(name)
		
		# --- Check for duplicity ---
		if name in frame:
			errorExit(ERROR_IDK, "Variable '{0}' already exist in global frame".format(name))
		
		# --- Create var in frame ---
		frame[name] = None;


	@classmethod
	def set(cls, name, value):
		# --- Identify frame ---
		frame = cls.__identifyFrame(name)
		
		# --- Check if exists ---
		if name not in frame:
			errorExit(ERROR_IDK, "Coudn't set value to non-existing variable '{0}'".format(name))
		
		# --- Get actual value ---
		if type(value) == var:	# If trying to add var (e.g. MOVE GF@aaa GF@bbb)
			value = value.getValue()	# Save its value not whole object
			
		# --- Save value to frame ---
		frame[name] = value;
		
		
	@classmethod	
	def get(cls, name):
		# --- Identify frame ---
		frame = cls.__identifyFrame(name)
		
		# --- Check if exists ---
		if name not in frame:
			errorExit(ERROR_IDK, "Variable '{0}' does not exist".format(name))
		
		# --- Get value from frame ---
		result = frame[name]
		
		# --- Check if initialized ---
		if type(result) == type(None):
			errorExit(ERROR_IDK, "Tried to get non-initilaized value")
		
		# --- Result ---
		return result;		
	
	
	@classmethod
	def __identifyFrame(cls, name):
		if name[:3] == "GF@":
			return cls.globalFrame
		elif name[:3] == "LF@":
			return cls.localFrame
		elif name[:3] == "TF@":
			return cls.temporaryFrame
		else:
			errorExit(ERROR_IDK, "Invalid frame prefix")


class Stack:
	"""Stack for values in IPPcode18"""
	def __init__(self):
		self.content = []
		
	def pop(self, dest):
		if len(self.content) == 0:
			errorExit(ERROR_MISSINGVALUE, "Cannot pop empty stack")
			
		if type(dest) != var:
			errorExit(ERROR_IDK, "Cannot pop to non-variable")
		
		value = self.content.pop()	# Pop top of the stack
		
		dest.setValue(value)	# Set the value
		
		
	def push(self, value):
		self.content.append(value)


class CallStack:	# @todo merge with classicStack
	content = []
	
	@classmethod
	def push(cls, value):
		cls.content.append(value)
	
	@classmethod	
	def pop(cls, dest):
		if len(cls.content) == 0:
			errorExit(ERROR_IDK, "Cannot pop empty call stack")
			
		return cls.content.pop()
		
	
		
		
class Labels:
	labels = {}
	
	@classmethod	
	def add(cls, name):
		name = str(name)	# Convert type label to str
		
		if name in cls.labels:
			errorExit(ERROR_SEMANTIC, "Label '{0}' already exists".format(name))
			
		cls.labels[name] = interpret.instrOrder
	
	@classmethod	
	def jump(cls, name):
		name = str(name)	# Convert type label to str
		
		if name not in cls.labels:
			errorExit(ERROR_SEMANTIC, "Label '{0}' does not exist".format(name))
			
		interpret.instrOrder = cls.labels[name]
		
		
class var:
	def __init__(self, name):
		self.name = name	
		
	def getValue(self):
		"""Returns value stored in var"""
		return Frames.get(self.getName())

	def getName(self):
		"""Returns name of var including frame prefix"""
		return self.name
	
	def setValue(self, value):
		Frames.set(self.getName(), value)
			
	
	# == Actual value convert method ==
	def __str__(self):
		value = self.getValue()
		
		if type(value) != str:
			errorExit(ERROR_IDK, "Cannot convert non-string variable to string")
			
		return value
		
	def __int__(self):
		value = self.getValue()
		
		if type(value) != int:
			errorExit(ERROR_IDK, "Cannot convert non-string variable to int")
			
		return value
	
	def __bool__(self):
		value = self.getValue()
		
		if type(value) != bool:
			errorExit(ERROR_IDK, "Cannot convert non-string variable to bool")
			
		return value	
		
		
class symb:
	"""Dummy class representing str, int, bool or var in instruction.checkArgumentes()"""
	pass
	
class label:
	def __init__(self, name):
		self.name = name
	
	def __str__(self):
		return self.name
		
				
	
class Interpret():
	def __init__(self):
		self.instrOrder = 1
		self.stack = Stack()
		
	def loadInstructions(self, root):
		# --- Search all nodes ---
		instrNodes = root.findall("./")
		instrNodesCount = len(instrNodes)
		
		# --- Search for LABEL nodes ---
		self.__findLabels(instrNodes)
		self.instrOrder = 1	# Reset instruction counter
			
		# --- Cycle throught every node ---
		while self.instrOrder <= instrNodesCount:	# Watchout! instrOrder starts at 1
			# -- Get current node --
			node = instrNodes[self.instrOrder-1]
			
			# -- Skip LABEL nodes --
			if node.attrib["opcode"].upper() == "LABEL":
				self.instrOrder = self.instrOrder+1
				continue	# They are already loaded by __findLabels()
			
			# -- Debug info --
			logger.debug("=============")
			logger.debug("{0} {1} ".format(node.tag, node.attrib))
			for arg in node:
				logger.debug("{0} {1} {2}".format(arg.tag, arg.attrib,arg.text))
			
			# -- Processing instruction --
			instruction = Instruction(node)
			instruction.execute()
			
			# -- Add counter --
			self.instrOrder = self.instrOrder+1
	
	
	def __findLabels(self, instrNodes):
		"""Search every label instruction used and saves it"""
		for node in instrNodes:
			if node.attrib["opcode"].upper() == "LABEL":
				self.instrOrder = int(node.attrib["order"])	# This is read from Labels.add
				instruction = Instruction(node)
				instruction.execute()
				
		
	
	def convertValue(self, xmlType, xmlValue):
		"""Converts XML value (str in python) to actual type (int, str, bool or var)"""
		
		# --- Variable type ---
		if xmlType == "var":
			if not re.search(r"^(LF|TF|GF)@[\w_\-$&%*][\w\d_\-$&%*]*$", xmlValue):
				errorExit(ERROR_IDK, "Invalid var name")
				
			return var(xmlValue)
		
		# --- Integer type ---		
		elif xmlType == "int":
			if not re.search(r"^[-+]?\d+$$", xmlValue):
				errorExit(ERROR_IDK, "Invalid int value")		
			
			return int(xmlValue)	# Convert str to int	
			
		# --- String type ---
		elif xmlType == "string":
			#if re.search(r"(?!\\[0-9]{3})[\s\\#]", xmlValue):	# @see parse.php for regex legend
			#	errorExit(ERROR_IDK, "Illegal character in string")	# @todo check the regex
			
			# -- Decode escape sequence --
			groups = re.findall(r"\\([0-9]{3})", xmlValue)	# Find escape sequences
			groups = list(set(groups))	# Remove duplicates
			
			for group in groups:
				if group == "092":	# Special case for \ (I don't even know why)
					xmlValue = re.sub("\\\\092", "\\\\", xmlValue)
					continue
				xmlValue = re.sub("\\\\{0}".format(group), chr(int(group)), xmlValue)
			
			return xmlValue
		
		# --- Boolean type ---
		elif xmlType == "bool":
			if xmlValue == "true":
				boolean = True
			elif xmlValue == "false":
				boolean = False
			else:
				errorExit(ERROR_IDK, "Invalid bool value (given {0})".format(xmlValue))
			
			return boolean
			
		# --- Type type ---
		if xmlType == "type":
			if not re.search(r"^(int|string|bool)$", xmlValue):
				errorExit(ERROR_IDK, "Invalid type value")
				
			return xmlValue
			
		# --- Type label ---
		if xmlType == "label":
			if not re.search(r"^[\w_\-$&%*][\w\d_\-$&%*]*$", xmlValue):
				errorExit(ERROR_IDK, "Invalid label name")
				
			return label(xmlValue)	
			
		# --- Invalid type ---
		else:
			errorExit(ERROR_IDK, "Unknown argument type (given {0})".format(xmlType))
	
	
	
class Instruction():
	def __init__(self, node):
		'''Initialization of internal strcture of XML <instruction> node'''
		
		# --- Check node ---
		if node.tag != "instruction":
			errorExit(ERROR_IDK, "Wrong node loaded (Expected instruction)")
		
		# --- Order check ---
		if int(node.attrib["order"]) != interpret.instrOrder:
			errorExit(ERROR_IDK, "Wrong instruction order")
		
		# --- Process node ---
		self.opCode = node.attrib["opcode"].upper()	
		self.args = self.__loadArguments(node)
		self.argCount = len(self.args)
		
		
	def __loadArguments(self, instrNode):	
		'''Loads child nodes (<argX>) of <instruction> node'''
		args = []
		argIndex = 0	
		
		# --- Load child nodes ---
		for argNode in instrNode:
			# -- Check arg node --
			if argNode.tag != "arg{0}".format(argIndex+1):
				errorExit(ERROR_IDK, "Wrong node loaded (Expected arg{0})".format(argIndex+1))
		
			# --- Save arg value ---
			args.append(interpret.convertValue(argNode.attrib["type"], argNode.text))
			argIndex = argIndex+1
			
		return(args)
	
	
	def __checkArguments(self, *expectedArgs):	
		#DEBUG
		#print(self.argCount)
		#print(len(expectedArgs))
		#print(expectedArgs)
		
		# --- Checking arguments count ---
		if self.argCount != len(expectedArgs):
			errorExit(ERROR_IDK, "Invalid argument count")
			
		# --- Converting tuple to list ---
		expectedArgs = list(expectedArgs)	
			
		# --- Checking arguments type ---
		i = 0;
		for arg in self.args: # Check every argument
			# -- Replacing <symb> --
			if expectedArgs[i] == symb:
				expectedArgs[i] = [int, bool, str, var]
			
			
			argType = type(arg)	# Saved argument's type
			
			# -- Only one allowed type --
			if type(expectedArgs[i]) == type:
				if argType != expectedArgs[i]:
					errorExit(ERROR_IDK, "Invalid argument type (expected {0} given {1})".format(expectedArgs[i],argType))
					
			# -- More allowed types --
			elif type(expectedArgs[i]) == list:
				if argType not in expectedArgs[i]:	# Check if used argument has one of expected types
					errorExit(ERROR_IDK, "Invalid argument type (expected {0} given {1})".format(expectedArgs[i],argType))
					
			# -- Wrong method parameters --
			else:
				errorExit(ERROR_IDK, "Illegal usage of Instruction.checkArguments()")
				
			i = i+1
	
	def __checkVarType(self, variable, expected):
		'''Compares expected and actula variable type if called on variable'''
		if type(variable) != var:
			return
		
		if type(variable.getValue()) != expected:
			errorExit(ERROR_OPERANDS, "Wrong type inside variable (expected {0} given {1})".format(expected, variable.getType()))
			
		
	
	def execute(self):
		if self.opCode == "DEFVAR":
			self.DEFVAR()
		elif self.opCode == "ADD":
			self.ADD()
		elif self.opCode == "SUB":
			self.SUB()
		elif self.opCode == "MUL":
			self.MUL()
		elif self.opCode == "IDIV":
			self.IDIV()
		elif self.opCode == "WRITE":
			self.WRITE()
		elif self.opCode == "MOVE":
			self.MOVE()
		elif self.opCode == "PUSHS":
			self.PUSHS()
		elif self.opCode == "POPS":
			self.POPS()
		elif self.opCode == "STRLEN":
			self.STRLEN()
		elif self.opCode == "CONCAT":
			self.CONCAT()
		elif self.opCode == "GETCHAR":
			self.GETCHAR()
		elif self.opCode == "SETCHAR":
			self.SETCHAR()
		elif self.opCode == "TYPE":
			self.TYPE()
		elif self.opCode == "AND":
			self.AND()
		elif self.opCode == "OR":
			self.OR()
		elif self.opCode == "NOT":
			self.NOT()
		elif self.opCode == "LT":
			self.LT()
		elif self.opCode == "EQ":
			self.EQ()
		elif self.opCode == "GT":
			self.GT()
		elif self.opCode == "INT2CHAR":
			self.INT2CHAR()
		elif self.opCode == "STRI2INT":
			self.STRI2INT()
		elif self.opCode == "READ":
			self.READ()
		elif self.opCode == "LABEL":	# Called from Interpret.__findLabels()
			self.LABEL()	
		elif self.opCode == "JUMP":
			self.JUMP()
		elif self.opCode == "JUMPIFEQ":
			self.JUMPIFEQ_JUMPIFNEQ(True)
		elif self.opCode == "JUMPIFNEQ":
			self.JUMPIFEQ_JUMPIFNEQ(False)		
		elif self.opCode == "DPRINT" or self.opCode == "BREAK":
			pass
		elif self.opCode == "CREATEFRAME":
			self.CREATEFRAME()
		elif self.opCode == "PUSHFRAME":
			self.PUSHFRAME()
		elif self.opCode == "CALL":
			self.CALL()
		elif self.opCode == "RETURN":
			self.RETURN()
		else:	# @todo more instructions
			errorExit(ERROR_IDK, "Unknown instruction")	
	
	
	# === IPPcode18 methods ===
		
	# --- Instrcution DEFVAR ---
	def DEFVAR(self):
		self.__checkArguments(var)
		
		Frames.add(self.args[0].getName())	
		
		
	# --- Instrcution ADD ---
	def ADD(self):
		self.__checkArguments(var, [int, var], [int, var])

		# -- Count and save result --
		result = int(self.args[1]) + int(self.args[2])	
		self.args[0].setValue(result)
		
		
	# --- Instrcution SUB ---
	def SUB(self):
		self.__checkArguments(var, [int, var], [int, var])

		# -- Count and save result --
		result = int(self.args[1]) - int(self.args[2])	
		self.args[0].setValue(result)

		
	# --- Instrcution ADD ---
	def MUL(self):
		self.__checkArguments(var, [int, var], [int, var])

		# -- Count and save result --
		result = int(self.args[1]) * int(self.args[2])	
		self.args[0].setValue(result)
		
		
	# --- Instrcution ADD ---
	def IDIV(self):
		self.__checkArguments(var, [int, var], [int, var])

		# -- Check for zero divide --
		if int(self.args[2]) == 0:
			errorExit(ERROR_ZERODIVIDE, "Tried to divide by zero")

		result = int(self.args[1]) // int(self.args[2])	
		
		self.args[0].setValue(result)
		
		
	# --- Instrcution WRITE ---
	def WRITE(self):
		self.__checkArguments(symb)
	
		# --- Get value stored in var ---
		if type(self.args[0]) == var:
			value = self.args[0].getValue()
		else:
			value = self.args[0]

		# --- Prepare print for bool ---
		if type(value) == bool:
			if value == True:
				value = "true"
			else:
				value = "false"
		
		result = str(value)
			
		print(result)


	# --- Instrcution MOVE ---
	def MOVE(self):
		self.__checkArguments(var, symb)
		
		self.args[0].setValue(self.args[1])
		
		
	# --- Instrcution PUSHS ---
	def PUSHS(self):
		self.__checkArguments(symb)
	
		interpret.stack.push(self.args[0])


	# --- Instrcution POPS ---
	def POPS(self):
		self.__checkArguments(var)
	
		interpret.stack.pop(self.args[0])
		
		
	# --- Instrcution STRLEN ---
	def STRLEN(self):
		self.__checkArguments(var, [str, var])
		
		result = len(str(self.args[1]))
	
		self.args[0].setValue(result)
		
		
	# --- Instrcution CONCAT ---
	def CONCAT(self):
		self.__checkArguments(var, [str, var], [str, var])
	
		result = str(self.args[1]) + str(self.args[2])
	
		self.args[0].setValue(result)
		
		
	# --- Instrcution GETCHAR ---
	def GETCHAR(self):
		self.__checkArguments(var, [str, var], [int, var])
	
		string = str(self.args[1])
		position = int(self.args[2])
		
		if position >= len(string):
			errorExit(ERROR_STRING, "GETCHAR/STRI2INT position out of range")
		
		result = string[position]
	
		self.args[0].setValue(result)
		
		
	# --- Instrcution GETCHAR ---
	def SETCHAR(self):
		self.__checkArguments(var, [int, var], [str, var])
	
		string = str(self.args[0])
		position = int(self.args[1])
		character = str(self.args[2])
		
		if position >= len(string):
			errorExit(ERROR_STRING, "SETCHAR position out of range")
		if len(character) == 0:
			errorExit(ERROR_STRING, "SETCHAR replacement character not given")
		
		result = string[:position] + character[0] + string[position+1:]
	
		self.args[0].setValue(result)
		
		
	# --- Instrcution TYPE ---	
	def TYPE(self):
		self.__checkArguments(var, symb)
		
		# -- Get value inside var --
		if type(self.args[1]) == var:
			value = self.args[1].getValue()
		else:
			value = self.args[1]
		
		# -- Convert value type name to str --	
		valueType = re.search(r"<class '(str|bool|int)'>", str(type(value))).group(1)
		
		# -- Rename str to string --
		if valueType == "str":
			result = "string"
		else:
			result = valueType
			
		# -- Save value --
		self.args[0].setValue(result)


	# --- Instrcution AND ---	
	def AND(self):
		self.__checkArguments(var, [bool, var], [bool, var])
		
		result = bool(self.args[1]) and bool(self.args[2])
		
		self.args[0].setValue(result)
		
		
	# --- Instrcution OR ---	
	def OR(self):
		self.__checkArguments(var, [bool, var], [bool, var])
		
		result = bool(self.args[1]) or bool(self.args[2])
		
		self.args[0].setValue(result)


	# --- Instrcution NOT ---	
	def NOT(self):
		self.__checkArguments(var, [bool, var])
		
		result = not bool(self.args[1])
		
		self.args[0].setValue(result)
		
		
	# --- Instrcution LT ---	
	def LT(self):
		self.__checkArguments(var, symb, symb)
		
		# -- Get values inside var --
		if type(self.args[1]) == var:
			valueA = self.args[1].getValue()
		else:
			valueA = self.args[1]
			
		if type(self.args[2]) == var:
			valueB = self.args[2].getValue()
		else:
			valueB = self.args[2]
		
		# -- Check for same type --
		if type(valueA) != type(valueB):
			errorExit(ERROR_IDK, "Can't compare different types")
		
		# -- Compare values --
		result = valueA < valueB
		
		# -- Save result --
		self.args[0].setValue(result)
		
		
	# --- Instrcution EQ ---	
	def EQ(self):
		self.__checkArguments(var, symb, symb)
		
		# -- Get values inside var --
		if type(self.args[1]) == var:
			valueA = self.args[1].getValue()
		else:
			valueA = self.args[1]
			
		if type(self.args[2]) == var:
			valueB = self.args[2].getValue()
		else:
			valueB = self.args[2]
		
		# -- Check for same type --
		if type(valueA) != type(valueB):
			errorExit(ERROR_IDK, "Can't compare different types")
		
		# -- Compare values --
		result = valueA == valueB
		
		# -- Save result --
		self.args[0].setValue(result)
		
		
	# --- Instrcution GT ---	
	def GT(self):
		self.__checkArguments(var, symb, symb)
		
		# -- Get values inside var --
		if type(self.args[1]) == var:
			valueA = self.args[1].getValue()
		else:
			valueA = self.args[1]
			
		if type(self.args[2]) == var:
			valueB = self.args[2].getValue()
		else:
			valueB = self.args[2]
		
		# -- Check for same type --
		if type(valueA) != type(valueB):
			errorExit(ERROR_IDK, "Can't compare different types")
		
		# -- Compare values --
		result = valueA > valueB
		
		# -- Save result --
		self.args[0].setValue(result)
		
		
	# --- Instrcution INT2CHAR ---	
	def INT2CHAR(self):
		self.__checkArguments(var, [int, var])
		
		value = int(self.args[1])
		
		try:
			result = chr(value)
		except ValueError:
			errorExit(ERROR_STRING, "INT2CHAR invalid character code")
		
		# -- Save result --
		self.args[0].setValue(result)	
		
		
	# --- Instrcution STRI2INT ---	
	def STRI2INT(self):
		self.GETCHAR()	# Too lazy
		
		result = ord(self.args[0].getValue())
		
		# -- Save result --
		self.args[0].setValue(result)	
		
		
	# --- Instrcution READ ---	
	def READ(self):
		self.__checkArguments(var, str)	# Should be <var> <type> but I'm going to bed
		
		inputStr = input()
		
		# -- Bool input special rules --
		if self.args[1] == "bool":
			if inputStr.lower() == "true":
				inputStr = "true"
			else:
				inputStr = "false"
		
		# -- Convert input type --
		result = interpret.convertValue(self.args[1], inputStr)
		
		# -- Save result --
		self.args[0].setValue(result)	
		
		
	# --- Instrcution LABEL ---	
	def LABEL(self):	# Called from Interpret.__findLabels()
		self.__checkArguments(label)
		
		Labels.add(self.args[0])


	# --- Instrcution JUMP ---	
	def JUMP(self):
		self.__checkArguments(label)
		
		Labels.jump(self.args[0])
		
		
	# --- Instrcutions JUMPIFEQ & JUMPIFNEQ ---	
	def JUMPIFEQ_JUMPIFNEQ(self, expectedResult):
		self.__checkArguments(label, symb, symb)
		
		# -- Get values inside var --
		if type(self.args[1]) == var:
			valueA = self.args[1].getValue()
		else:
			valueA = self.args[1]
			
		if type(self.args[2]) == var:
			valueB = self.args[2].getValue()
		else:
			valueB = self.args[2]
		
		# -- Check for same type --
		if type(valueA) != type(valueB):
			errorExit(ERROR_IDK, "Can't compare different types")
		
		# -- Compare values --
		result = valueA == valueB
		
		# -- Jump if condition is met --
		if result == expectedResult:
			Labels.jump(self.args[0])
			
			
	# --- Instrcution CREATEFRAME ---	
	def CREATEFRAME(self):
		self.__checkArguments()
		
		# -- Reset TF --
		Frames.temporaryFrame = {}
		
		
	# --- Instrcution PUSHFRAME ---	
	def PUSHFRAME(self):
		self.__checkArguments()
		
		if Frames.temporaryFrame == None:
			errorExit(ERROR_NOTEXISTSCOPE, "Tried to access not defined frame")
		
		# -- Move TF to stack --
		Frames.stack.append(Frames.temporaryFrame)
		
		# -- Set LF --
		Frames.localFrame = Frames.stack[-1]	# LF = top of the stack (previously TF)
			
		# -- Reset TF --
		Frames.temporaryFrame == None
		
		
	# --- Instrcution POPFRAME ---	
	def POPFRAME(self):		
		self.__checkArguments()

		# -- Check if LF exists --		
		if Frames.localFrame == None:
			errorExit(ERROR_NOTEXISTSCOPE, "Local frame not defined")
			
		# -- Set TF --
		Frames.temporaryFrame = Frames.stack.pop()	# TF = previous top of the stack (LF)
		
		# -- Reset LF --
		Frames.localFrame == None
		
		
	# --- Instrcution CALL ---	
	def CALL(self):		
		CallStack.push(interpret.instrOrder)
		
		self.JUMP()
		
		
	# --- Instrcution RETURN ---	
	def RETURN(self):	
		self.__checkArguments()
			
		interpret.instrOrder = CallStack.pop()	
		
		
main()
