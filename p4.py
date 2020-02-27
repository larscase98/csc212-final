#!/usr/bin/env python 

from subprocess import Popen, DEVNULL
import shlex, os, errno, time, glob

#Constants for later use
of2_verbose = False
temp_output = "of2_out"
temp_output_file = temp_output + '.csv'
landmark_count = 68

#This line finds the openface software
#If you're getting an error here, make sure this file is in the same folder as your openface installation
exe = ([exe for exe in glob.glob("./**/FeatureExtraction", recursive=True) if os.path.isfile(exe)]+[exe for exe in glob.glob(".\\**\\FeatureExtraction.exe", recursive=True)])[0]

#Clean up the temp file from a previous run, if it exists
try:
	os.remove(temp_output_file)
except OSError as e: 
	if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
		raise # re-raise exception if a different error occurred

#These lines write the command to run openface with the correct options
command = shlex.split(" -device 0 -out_dir . -pose -2Dfp -of "+temp_output)
command.insert(0, exe)

#This line starts openface
of2 = Popen(command, stdin=DEVNULL, stdout=(None if of2_verbose else DEVNULL), stderr=DEVNULL)

#This loop waits until openface has actually started, as it can take some time to start producing output
while not os.path.exists(temp_output_file):
	time.sleep(.5)

#Openface saves info to a file, and we open that file here
data = open(temp_output_file,'r')

#This loop repeats while openface is still running
#Inside the loop, we read from the file that openface outputs to and check to see if there's anything new
#We handle the data if there is any, and wait otherwise
shockDetected=False;
smileDetected=False;
pitch_prev, yaw_prev, roll_prev = 0, 0, 0
pitch_count, yaw_count, roll_count = 0, 0, 0
pitch_nodding, yaw_nodding, roll_nodding = False, False, False
pitch_hasPrinted, yaw_hasPrinted, roll_hasPrinted = False, False, False
while(of2.poll() == None):
	line = data.readline().strip()
	if(line != ""):
		try:
			#Parse the line and save the useful values
			of_values = [float(v) for v in line.split(', ')]
			timestamp, confidence, success = of_values[2:5]
			pitch, yaw, roll = of_values[8:11]
			landmarks = []
			for i in range(11,11+landmark_count):
				landmarks.append((of_values[i],of_values[i+landmark_count]))
		except ValueError:
			#This exception handles the header line
			continue
		
		## FACIAL EXPRESSION SECTION
		
		#Surprise variables
		
		noseTop = landmarks[29]
		noseBott = landmarks[30]
		baselineDist = noseBott[1]-noseTop[1]

		#print(baselineDist)
		eyebrowL = landmarks[19]
		eyebrowR = landmarks[24]
		eyebrowBottL=landmarks[37]
		eyebrowBottR=landmarks[44]

	
		rSmileTip = landmarks[54]
		lSmileTip = landmarks[48]
		centerSmile =landmarks[57]
		bottRightSmile = landmarks[57]
		
		smileValR = centerSmile[1]-rSmileTip[1]
		smileValL = centerSmile[1]-lSmileTip[1]
		#print(smileValR,"\t",smileValL,"\t", baselineDist)

		topL = landmarks[61] #uses three points on top and bottom of the lip
		topM = landmarks[62]
		topR=landmarks[63]
		
		bottL = landmarks[67]
		bottM = landmarks[66]
		bottR = landmarks[65]
		#print("\t",(eyebrowBottL[1]-eyebrowL[1]))
		
		leftSurprise = topL[1] - bottL[1]
		midSurprise = bottM[1] - topM[1]
		rightSurprise = topR[1] - bottR[1]

		sideFace = landmarks[13]
		#smileDist = sideFace[0]+rSmile[0]
		
		eyebrowHeight= eyebrowBottL[1] - eyebrowL[1]

		#print(smileDist,"\t", baselineDist)
		#if(smileValR+smileValL<-20 and leftSurprise>-14 and midSurprise>-20):
		#print(smileDist,"\t", baselineDist)

		if (not smileDetected) and (smileValR > baselineDist * 1.5) and (smileValL>baselineDist * 1.5) and 
		   (eyebrowHeight<baselineDist * 2.5)  and (midSurprise<baselineDist*1.2):
			print("SMILE DETECTED")
			smileDetected=True

		if (smileDetected) and (smileValR < baselineDist * 1.2) and (smileValL<baselineDist*1.2):
			smileDetected=False;
			print("reset smile","\n")


		#print(midSurprise,"\t", baselineDist)
		
		#print(eyebrowHeight,"\t", baselineDist)
		
		if (not shockDetected) and ((eyebrowBottL[1] - eyebrowL[1]) > baselineDist * 2.5) and (midSurprise>baselineDist*2):
			print("SHOCKED")
			shockDetected=True

		
		if (shockDetected):
			#print("waiting to reset")
			if (eyebrowBottL[1] - eyebrowL[1]) < baselineDist * 2 and (midSurprise<baselineDist):
				shockDetected=False
				print("reset shock","\n")

		## NODDING SECTION

		# track derivative of pitch, roll, and yaw
		pitch_diff = pitch - pitch_prev
		yaw_diff = yaw - yaw_prev
		roll_diff = roll - roll_prev
		pitch_prev, yaw_prev, roll_prev = pitch, yaw, roll
		
		# add to nodding counter if not already registered as nodding
		# decrease counter if not nodding
		if (abs(pitch_diff) > .05) and (not pitch_nodding):
			pitch_count += 1
		elif pitch_count > 0:
			pitch_count += -1
		if abs(yaw_diff) > .05 and (not yaw_nodding):
			yaw_count += 1
		elif yaw_count > 0:
			yaw_count += -1
		if (abs(roll_diff) > .05) and (not roll_nodding):
			roll_count += 1
		elif roll_count > 0:
			roll_count += -1
			
		# if nod count ever reaches 0, reset booleans
		if pitch_count == 0:
			pitch_nodding = False
			pitch_hasPrinted = False
		if yaw_count == 0:
			yaw_nodding = False
			yaw_hasPrinted = False
		if roll_count == 0:
			roll_nodding = False
			roll_hasPrinted = False
		
		# change nodding boolean if counter reaches threshold
		if (pitch_count > 6) and (not pitch_nodding): # count threshold chosen to tune detection sensitivity
			pitch_nodding = True
		if (yaw_count > 6) and (not yaw_nodding):
			yaw_nodding = True
		if (roll_count > 6) and (not roll_nodding):
			roll_nodding = True
		
		# print based on booleans
		if (pitch_nodding) and (not pitch_hasPrinted):
			print("Yes")
			pitch_hasPrinted = True
		if (yaw_nodding) and (not yaw_hasPrinted):
			print("No")
			yaw_hasPrinted = True
		if (roll_nodding( and (not roll_hasPrinted):
			print("Indian Nod")
			roll_hasPrinted = True
		
	else:
		time.sleep(.01)
	
#Reminder: press 'q' to exit openface

print("Program ended")

data.close()
