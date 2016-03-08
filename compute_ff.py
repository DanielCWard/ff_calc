import numpy as np
import csv
from scipy import ndimage
import os.path
import dicom as pydi
import pylab
import glob
import natsort
from natsort import natsorted
import nibabel as nib
import easygui as gui
import Tkinter
from Tkinter import *
WHITE = 1000
BLACK = 0


#def main function which gets infor form the dicom file
#and calculates the fat fratcions
def process_file(niFileName, dicomDirPath):
	dicomPath = get_dicom_from_nii(filename, dicomDirPath)
	dicomList = sort_dicom_seq(dicomPath)
	dicomData = pydi.read_file(dicomList[0])
	voxVol = get_dicom_voxel_size(dicomData)
	voxArr = get_im_as_array(dicomData)
	dimen = get_dimensions(voxArr)
	height = dimen[1]
	width = dimen[0]
	slices = get_segmented_vox(dicomList, segment, width, height)
	pd = get_patient_data(dicomData)
	ff = calc_fat_vol(slices, voxVol, lwrB, uprB, lwrW, uprW, width, height)
	wr.writerow([ff[0], ff[1], ff[2], ff[3], ff[4], ff[5], ff[6], ff[7], ff[8], ff[9], ff[10], ff[11], ff[12], ff[13], ff[14], pd[0], pd[1], pd[2], pd[3], pd[4], pd[5], pd[6], pd[7], pd[8])


#does most of the processing
def main(niFilePath, dicomDirPath, csvPath):
	i = 0
	name = ['PSCID', 'FF %', 'FF Vol cm^3', 'FF abs Min', 'FF avg Min', 'FF abs Max', 'FF avg Max', 'BAT %', 'BAT Vol cm^3',  'BAT abs Min', 'BAT avg Min', 'BAT abs Max', 'BAT avg Max', 'WAT %', 'WAT Vol cm^3', 'WAT abs Min', 'WAT avg Min', 'WAT abs Max', 'WAT avg Max', "Patient Size", "Patient Weight", "Patient Sex", "Age", "DOB", "Study ID", "Study Time", "Magnetic Field Strength"]
	csvFile = open(csvPath, 'wb')
	wr = csv.writer(csvFile)
	wr.writerow(name)
	if singlePatient == True:
		process_file(niFilePath, dicomDirPath)
		return
	for filename in glob.glob(niFilePath):
		process_file(fileName, dicomDirPath)
	
#Goes through and selects all the files for processing
def get_dicom_from_nii(niFileName, dicomDirPath):
	patientNum = niFileName.split('/')[-1] #gets the 
	patientDicomPath = get_patient_folder(dicomDirPath, patientNum)
	return patientDicomPath

#gets the paitient data and scan data from the header from the dicom file
#erturns PID, weight, height, DOB, Age, Sex, Study ID, Study time, study data
#and magnetic field strength
def get_patient_data(data):
	patientData = []
	patientData.append(getattr(data, "PatientID", '')
	patientData.append(getattr(data, "PatientSize", '')
	patientData.append(getattr(data, "PatientWeight", '')
	patientData.append(getattr(data, "PatientSex", '')
	patientData.append(getattr(data, "PatientAge", '')
	patientData.append(getattr(data, "PatientBirthDate", '')
	patientData.append(getattr(data, "StudyID", '')
	patientData.append(getattr(data, "StudyDate", '')
	patientData.append(getattr(data, "MagneticFieldStrength", '')
	return patientData
	
#returns a particular directory for a patient number
#based on the segementation file name
def get_patient_folder(dicomDirPath, patientNum):
	path = None
	# Find folder of patient based on number
	for dirpath in glob.glob(dicomDirPath):
		if patientNum in dirPath:
			path = dicomDirPath.append(dirpath)	
	# Find relevent MRI folder in patient folder
	for i in glob.glob(path):
		if "MRI_RESEARCH" in dirpath or "MRI_BRAIN" in i:
			path = dicomDirPath.append(i)
	#Find specific BAT MRI folder
	for f in glob.glob(path):
		if "AX" in f and "SCAPULA" in f:
			if "FP" in f or "FF" in f:
				return path.append(f)
		 

#Takes a nii.gz img array and slice number(z coord) and returns the pixel array for that slice
def get_slice_arr(img, width, height, sliceNum):
	#Create 16 bit numpy array
	#Assume image[x][y][z] (it follows logical coord systems)
	#Create array in same format as the IMA images => arr[y][x]
	imgSlice = []
	image = img.get_data()
	for j in range(height - 1):
		row = []
		for i in range(width - 1):
			row.append(image[i][j][sliceNum])
		imgSlice.append(row)
	return imgSlice

# https://pyscience.wordpress.com/2014/09/08/dicom-in-python-importing-medical-image-data-into-numpy-with-pydicom-and-vtk/
#Returns the voxel size and slice thickness in mm for the dicom image
def get_dicom_voxel_size(img):
	voxelSize = (float(img.PixelSpacing[0]), float(img.PixelSpacing[1]), float(img.SliceThickness))
	return voxelSize

#retuns a pixel array of the opened image	
def get_im_as_array(img):
	voxArr = img.pixel_array
	return voxArr

#Returns tuple (width, height) of the DICOM file
def get_dimensions(voxArr):
        height = voxArr.shape[1]
        width = voxArr.shape[0]
        return (width, height)

#Returns the section of the dicom image which was identified as brown fat in the nii.gz file
def sort_dicom_seq(dirPath):
	dicomList = []
	for filename in glob.glob(dirPath):
		dicomList.append(filename)
		#print filename
	dicomList = natsorted(dicomList)
	return dicomList
		
#Displays the current pixel array as an image for testing purposes
def view_pix(pix):
        pylab.imshow(pix, cmap=pylab.cm.bone)
        pylab.show()


#Returns an array of slices. Each slice contains only pixels which are segmented
def get_segmented_vox(dicomList, segment, width, height):
	slices = []
	for sliceNum in range(len(dicomList)):
		img = pydi.read_file(dicomList[sliceNum])#lstFilesDCM[0])
        	voxArr = get_im_as_array(img)
		segVoxArr = get_slice_arr(segment, width, height, sliceNum)
		maskedSlice = mask_by_seg(segVoxArr, voxArr, width, height)
		if maskedSlice != None:
			slices.append(maskedSlice)
	#print len(slices)
	return slices
				
def mask_by_seg(segVoxArr, voxArr, width, height):
	segmented = False
	for i in range(width - 1):
		for j in range(height - 1):
			if segVoxArr[j][i] == BLACK:
				voxArr[j][i] = BLACK
			else:
				segmented = True

        if segmented == True:
		return voxArr
	else:
		return None


#Removes all voxels within an array of slices which are within a range
#Voxels are removed by being set to black
#Returns the array of slices with the voxels removed
def rm_voxel_by_range(slices, width, height, lwrBound, uprBound):
	for image in slices:
                for i in range(width - 1):
                        for j in range(height - 1):
                                if image[j][i] >= lwrBound and image[j][i] <= uprBound:
					image[j][i] = BLACK
	return slices

#Calculates the number of voxels and the average voxel value
#within an array of slices which are within the range
#The average will be normalised to between 0 and 1 by divind by max voxel value: 1000
def count_voxels(slices, width, height, lwrBound, uprBound, voxVol):
	count = 0
	value = 0
	minVals = []
	maxVals = []
	curMin = 1000
	curMax = 0
	#print lwrBound, uprBound, "bounds"
	for image in slices:
		for i in range(width - 1):
	                for j in range(height - 1):
				if image[j][i] >= lwrBound and image[j][i] <= uprBound:
					count += 1
					value += image[j][i]
					if image[j][i] < curMin:
						curMin = image[j][i]
					if image[j][1] > curMax:
						curMax = image[j][i]
		minVals.append(curMin)
		maxVals.append(curMax)
	minVals.sort()
	maxVals.sort()
	minVal = minVals[0]
	maxVal = maxVals[-1]
	avgMin = sum(minVals) / float(len(minVals))
	avgMax = sum(maxals) / float(len(maxVals))
	average = (value / count) * 1.000
	average = average / 1000
	vol = vox_to_cm(count, voxVol)
	#print count
	return [average, vol, minVal, avgMin, maxVal, avgMax]

#Computes the real volume, from voxels to millimeters
#Dimen is a list of [x, y, z] size of voxel
def vox_to_cm(voxCount, dimen):
	voxVol = dimen[0] * dimen[1] * dimen[2]
	return voxCount * voxVol * 0.001

#Computes volumes of fat fraction, BAT and WAT
#Returns a list [(FFave, FFVol), (BATave, BATVol), (WATave, WATVol)]
def calc_fat_vol(slices, voxVol, BATlwr, BATupr, WATlwr, WATupr, width, height):
	#Calc volumes of all segmented fat
	ff = count_voxels(slices, width, height, (BATlwr * 10), (WATupr * 10), voxVol)
	#Mask image for WAT and repeat calc
	wat = count_voxels(slices, width, height, (WATlwr * 10), (WATupr * 10), voxVol)
	#Mask and repeat for BAT
	bat = count_voxels(slices, width, height, (BATlwr * 10), (BATupr * 10), voxVol)
	ffRet = []
	for i in ff:
		ffRet.append(i)
	for i in bat:
		ffRet.append(i)
	for i in wat:
		ffRet.append(i)
	return ffRet

#open the needed directory
def get_dicom_path():
        path = gui.diropenbox()
        return path

#open the needed directory
def get_segment_path():
        path = gui.fileopenbox()
        return path

def get_selected_vals():
	lwrB = lwrBat.get()
	uprB = uprBat.get()
	lwrW = lwrWat.get()
	uprW = uprWat.get()
        ffvals = calc_fat_vol(slices, voxVol, lwrB, uprB, lwrW, uprW)
	print "FF: ", ffvals[0]
	print "BAT: ", ffvals[1]
	print "WAT: ", ffvals[2]
#	name = ['FF %', 'FF Vol cm^3', 'BAT %', 'BAT Vol cm^3','WAT %', 'WAT Vol cm^3']
	wr.writerow([ffvals[0][0], ffvals[0][1], ffvals[1][0], ffvals[1][1], ffvals[2][0], ffvals[2][1]])

def save_file():
	wr.close()
#main function which handles everything
#def main_gui():
scaleLen = 120
dicomPath = get_dicom_path()
dicomPath = dicomPath + "/*.IMA"
segmentPath = get_segment_path()
segment = nib.load(segmentPath)
dicomList = sort_dicom_seq(dicomPath)
img = pydi.read_file(dicomList[0])
voxVol = get_dicom_voxel_size(img)
voxArr = get_im_as_array(img)
dimen = get_dimensions(voxArr)
height = dimen[1]
width = dimen[0]


name = ['PSCID', 'FF %', 'FF Vol cm^3', 'FF abs Min', 'FF avg Min', 'FF abs Max', 'FF avg Max', 'BAT %', 'BAT Vol cm^3',  'BAT abs Min', 'BAT avg Min', 'BAT abs Max', 'BAT avg Max', 'WAT %', 'WAT Vol cm^3', 'WAT abs Min', 'WAT avg Min', 'WAT abs Max', 'WAT avg Max', "Patient Size", "Patient Weight", "Patient Sex", "Age", "DOB", "Study ID", "Study Time", "Magnetic Field Strength"]
csvFile = open(dicomPath + "Fat_Fractions.csv", 'wb')
wr = csv.writer(csvFile)
#NEED TO WRITE THE FIRST ROW AS THE BAT AND WAT AND FF VALS!
wr.writerow(name)

slices = get_segmented_vox(dicomList, segment, width, height)
master = Tk()
#Load either a single patient or choose all paitients
Button(master, text='Choose Single Patient Folder', command=load_single_patient).pack()
Button(master, text='Load all Patients', command=load_all_patients).pack()
#Add the choices for different BAT values
labelBat = Label(master, text="BAT Lower")
labelBat.pack()
lwrBat = Scale(master, from_=0, to=100, length=600, tickinterval=5, orient=HORIZONTAL)
lwrBat.set(20)
lwrBat.pack()
labelBatU = Label(master, text="BAT Upper")
labelBatU.pack()
uprBat = Scale(master, from_=0, to=100, length=600, tickinterval=5, orient=HORIZONTAL)
uprBat.set(60)
uprBat.pack()
labelWat = Label(master, text="WAT Lower")
labelWat.pack()
lwrWat = Scale(master, from_=0, to=100, length=600,  tickinterval=5, orient=HORIZONTAL)
lwrWat.set(80)
lwrWat.pack()
labelWatU = Label(master, text="WAT Upper")
labelWatU.pack()
uprWat = Scale(master, from_=0, to=100, length=600, tickinterval=5, orient=HORIZONTAL)
uprWat.set(90)
uprWat.pack()
Button(master, text='Calculate Fat Fractions', command=get_selected_vals).pack()
#Button(master, text='Save File', command=save_file).pack()
master.mainloop()


#img = pydi.read_file("pic2.IMA")#lstFilesDCM[0])
#voxSize = get_dicom_voxel_size(img)
#voxArr = get_im_as_array(img)
#dimen = get_dimensions_img(voxArr)
#dicomList = sort_dicom_seq("/home/ariane/Documents/gusto/In/*.IMA")
#get_matching_files(dicomList)
