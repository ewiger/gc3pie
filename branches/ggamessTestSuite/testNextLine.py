import re	
import os.path
import gc3libs
	
#This class will be used to storne the patterns logic. Each pattern is assigned to a file. Each file can have 
# multiple patterns. 
#TODO: Each pattern can be assigned a label such as energy, gradient, etc. (do we need this?)
class TestNextLineOld:
	
	def __init__(self, name):
		self.name = name #file name, such as exam01.log
		self.LPattern = [] #patterns 
		self.LMatchedLine = [] #first | last - select first or last line from the lines that match 
		self.LFollowingLine = [] #first | last - select first or last line in a file AFTER matched lines
		self.LPositionInLine = [] #extract numerical value from the line at given position
		self.LValues = [] #target Values 
		self.LTolerances = [] #tolerances
		self.LLabel = [] #Label, such as energy, gradient, etc. 
    #Predefined tolerances

		self.tolC =  0.3
		self.tolD =  0.0001
		self.tolE =  0.00000001
		self.tolG =  0.00001
		self.tolH =  0.0001
		self.tolI =  0.0001
		self.tolL =  0.1
		self.tolO =  0.0001
		self.tolP =  0.0001
		self.tolR =  0.0001
		self.tolS =  0.01
		self.tolT =  0.000001
		self.tolV =  0.00000001
		self.tolW =  0.1
		self.tolX =  0.00001
		
#The function prepares data structures for the followint task:
# selects a group of lines that match regexp 
# within lines FOLLOWED by the matched ones selects the target line that contains the tested value.
# pattern - a regexp that extracts lines of interest
# matchedLinePosition = last | first | "" | "2" | 2, information about which matched line to select. 
# followingLinePosition = last | first | "" | "2" | 2, information about which line to select from the file. 
# positionInLine =  "4" | 4, information about which column WITHIN the line to select. 
# value - value to be compared with
# tol - tolerance between value and value extracted from the log file		
	def grepAndFollow(self, pattern, matchedLinePosition, followingLinePosition, positionInLine, value, tol, name):
		self.LPattern.append(pattern)  
		self.LMatchedLine.append(matchedLinePosition) 
		self.LFollowingLine.append(followingLinePosition)
		self.LPositionInLine.append(positionInLine)
		self.LValues.append(value)
		self.LTolerances.append(tol)
		self.LLabel.append(name)
		
#Compare valLog and valOK against the tolerance.	
	def chkabs(self,valLog, valOK, tol, label):
		val = abs(valOK - valLog)
		ret = " " + label + '=%.2E ' %(val)
		if (val > tol):
			
			return (False,ret)
		else:
			return (True,ret)
	
# Analyze the argument in LPositionInLine. Return the index of the column that correspond the a target value. 
	def checkPositionInLine(self, posInLine):
		try:
			selNo = int(posInLine)
			selNo = selNo - 1 #for array indexing
		except ValueError:
				gc3libs.log.debug("Could not convert %s to int, positionInLine must be integer", posiInLine)
				selNo = -1
		return selNo
	
# Analyze the argument in LMatched. Return the index of the line of interest. 
# first -> 1, 
# last -> 99
# numerical value (also as a text) -> numerical value
	
	def checkMatchedLine(self,matchedLine):
		if (type(matchedLine) == type(4) ): # a strange way of checking the integer type
			which = matchedLine
			return which
		elif ("last" in matchedLine.lower().strip()):
			which = 99 #encode the last position. Note that the number of matched lines is unknown at this stage
		elif ("first" in matchedLine.lower().strip()):
			which = 1
		elif (matchedLine == ""): #first is assumed
			which = 1
		else:
			#try to convert to int
			try:
				which = int(matchedLine)
				return which
			except ValueError:
				gc3libs.log.debug("ERROR: %s is incorrect. ",matchedLine)
				return -1
			which = -1
		return which
			
#Search for pattern in the file. Return a list of lines together with the line numbers. 
# The line numbers are used later by grepAndFollow()
	
	def grepFile(self, filename, pattern, whichFollowing = 0):
		regexp = re.compile(pattern, re.VERBOSE) #  
		FILE = open(filename, 'r')
		lines = FILE.readlines()
		FILE.close()
		#Store line numbers that match regexp
		matchedLineNumbers = []
		matchedLinesTemp = []
		lenLines = len(lines)

		#Enumerate the lines
		for num, line in enumerate(lines):
			match = regexp.search(line.strip())
			if match:
				matchedLineNumbers.append(num)
				matchedLinesTemp.append(line)
		return (matchedLineNumbers,matchedLinesTemp)
		 
	#Extract num+whichFollowing line number from the file. 
	def grepNext(self, filename, num, whichFollowing):	
		FILE = open(filename, 'r')
		lines = FILE.readlines()
		FILE.close()
		lenLines = len(lines) 		 
		if (whichFollowing > 0 ): 
 			sum = whichFollowing+num
			if (sum < lenLines-1):
					targetLine = lines[num+whichFollowing]
			else:
				if (self.DEBUG):
					gc3libs.log.debug("Out of boundary. Skipping.")
					gc3libs.log.debug("Length of file is: %s and the extracted line has a number %s.", lenLines, whichFollowing)
				return ""						
		return targetLine	

		
#Extract a SINGLE line from a map of detected lines with its line number.
	def getTargetLine(self, lineNumbersList, matchedLinesList, whichLine):
		lenT = len(matchedLinesList)
		numberCorrect = 0
		lineCorrect = ""
		if (whichLine <= 0 ):
			return (numberCorrect, lineCorrect)
			
		elif (whichLine==99):
			finalWich = lenT-1  
			lineCorrect = matchedLinesList[finalWich]	
			#print "LINE CORRECT", lineCorrect
			numberCorrect = lineNumbersList[finalWich]
		else: # whichLine > 0): #correct values
				finalWich = whichLine - 1 #starting from 0
				numberCorrect = lineNumbersList[finalWich]
				lineCorrect = matchedLinesList[finalWich].strip()
		return (numberCorrect, lineCorrect)
	
	
	def getValueFromLine(self, line, position):
		list = line.split()
		if (position > len(list)):
			gc3libs.log.debug("Out of boundary, check the position in the target line.")
			return ""
		try:
			value = float(list[position])
		except ValueError:
			gc3libs.log.debug("Could not convert to float, list(selNo) = %s must be flaat.",list[position])
			return ""
		return value
	
#Run each test. To optimize the execution each file is analyzed only ONCE. Internal lists drive the execution.
# 
#Internal parameters: 
# whichFolowing
# finalFlag is True only when all the tests return True
# finalString contains the test labels with results (Eerr=0.0E)
	def run(self):
		filename = self.name
		finalStr = ""
		finalFlag = True
		testNo = 0
		gc3libs.log.debug("Test: %s", self.name)
		gc3libs.log.debug("LPattern %s", self.LPattern)
		gc3libs.log.debug("LMatchedLine %s", self.LMatchedLine)
		gc3libs.log.debug("LFollowingLine %s", self.LFollowingLine) 
		gc3libs.log.debug("LPositionInLine %s", self.LPositionInLine) 
		gc3libs.log.debug("LValues %s", self.LValues)
		gc3libs.log.debug("LTolerances %s", self.LTolerances) 
		if (len(self.LPattern) == 0):
			gc3libs.log.debug("Empty test. Skipping.")
			return False
		
		for pattern, whichLine, followingLine, positionInLine, value, tolerance, label in zip(self.LPattern, self.LMatchedLine, self.LFollowingLine, self.LPositionInLine, self.LValues, self.LTolerances, self.LLabel):
			testNo = testNo + 1
			#Encode the index of the line of interest
			which = self.checkMatchedLine(whichLine)
			whichFollowing  = self.checkMatchedLine(followingLine)
			
			gc3libs.log.debug("Internal Test No. %s", testNo)
			gc3libs.log.debug("CHECKED MatchedLine %s", which)
			gc3libs.log.debug("CHECKED followingLine %s", whichFollowing)
			#Extract the position of the value within the target line	
			pos = self.checkPositionInLine(positionInLine)
			gc3libs.log.debug("CHECKED positionInLine %s", pos)
			if (whichFollowing < 0):
				gc3libs.log.debug("ERROR: whichFollowing %s is incorrect.",whichFollowing) 
				return False
			
			#Extract a list of lines that match a regexp and line indices as lists. 
			(numList,linesFound) = self.grepFile(filename, pattern) 
			
			# Nothing Found
			if (len(linesFound) == 0):
				gc3libs.log.debug("Nothing found with your regexp.")
				finalFlag = finalFlag and False
				continue
			
			(numLine, targetLineT) = self.getTargetLine(numList, linesFound, which)
			
			targetLine = self.grepNext(filename, numLine, whichFollowing)
			
			gc3libs.log.debug("MATCHED LINE: %s", targetLine)
		
			#Extract the value from matched line
			valL = self.getValueFromLine(targetLine, pos)
			if (valL == ""):
				gc3libs.log.debug("ERROR: Cannot retrieve the float value from line %s.", targetLine)
				return False
			else:
				gc3libs.log.debug("Comparing %s against %s.", valL, value)
				(flag, strOut) = self.chkabs(valL, value, tolerance, label)
			 	finalStr = finalStr + strOut
				finalFlag = finalFlag and flag
			
		return (finalFlag,finalStr)
	
	
#Scenarios
#grep a single line and seek for a value withing the line -> grep + awk
#grepAndAnalyze("Text", Nth matchedLine = first (default), position, ...)
#grep a set of lines, select first, last within matches, and analyze the line -> grep + sed
#grepAndAnalyze("Text", position, Nth matchedLine = last)
#grep a set of lines, select the next one in file and analyze it -> grep + last + cut -d : -f 1 (select 1 element from a line splitted by ':') + 
#grepAndFollow("Text", position, Nth following line = first)

#grep a set of lines, select LAST/ANY line in the file and analyze it #exam27
#grepAndFollow("Text", position, Nth following line = last, number?)

#Params:
#- a path to a directory with test files, "path_to_dir"
#- a path to a report file (optional, if missing stdout is used)
#- a path to pre-calculated results as log files or files with a desired pattern

#./testgms path_to_dir path_to_results ../report.log


# The aim of the project is to implement a tool for automated tests in GAMESS (testgms).
# The tool takes a directory with .inp files being tested and generates an output file with a report.
# Tests passed will be indicated as OK, otherwise the differences will be reported.
# 
# Example:
# ./testgms path_to_dir ../report.log path_to_results
# 
# Params:
# - a path to a directory with test files, "path_to_dir"
# - a path to a report file (optional, if missing stdout is used)
# - a path to pre-calculated results as log files or files with a desired pattern
# 
# The report is generated on the basis of:
# 1) existing results that are 100% correct (a gold standard). In this scenario each input file is paired to a complementary log file (exam01.inp is paired with exam01.log, examNUM.inp is paired with examNUM.log) and differences are reported.
# 2) log files with predefined patterns. The user prepares such a file by defining a pattern that must EXACTLY the same. In this scenario the algorithm tries to match a given output with a pattern. Differences are reported.
# 
	
	
#	def grep(self,pattern,fileObj):
#		r=[]
#  		for line in fileObj:
#			if re.search(pattern,line):
#				r.append(line)
#		return r
