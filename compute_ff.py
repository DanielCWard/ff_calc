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


#http://nipy.org/nibabel/nibabel_images.html
#Returns voxel in terms of dx, dy, dz and the time (ms) between slices of a nii.gz image
#Slice time will be omitted if the nii.gz image was computer (rather than machine/scanner) generated
#	[dx, dy, dz, sliceTime]
def get_nii_gz_voxel_vol(img):
	#Get header information
	header = img.header
	return header.get_zooms()

#Returns the output data shape of the .nii.gz image
#Slice time will be omitted if the nii.gz image was computer (rather than machine/scanner) generated
#       [x, y, z, sliceTime]
def get_nii_gz_shape(img):
	header = img.header
	return header.get_data_shape()

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

#http://nipy.org/nibabel/nibabel_images.html
#def get_nigz_metadata():


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
        #view_pix(voxArr)
	for i in range(width - 1):
		for j in range(height - 1):
			if segVoxArr[j][i] == BLACK:
				voxArr[j][i] = BLACK
			else:
				segmented = True

        if segmented == True:
	#	view_pix(segVoxArr)
       	#	view_pix(voxArr)
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
def count_voxels(slices, width, height, lwrBound, uprBound):
	count = 0
	value = 0
	#print lwrBound, uprBound, "bounds"
	for image in slices:
		for i in range(width - 1):
	                for j in range(height - 1):
				if image[j][i] >= lwrBound and image[j][i] <= uprBound:
					count += 1
					value += image[j][i]
	average = (value / count) * 1.000
	average = average / 1000
	#print count
	return (count, average)

#Computes the real volume, from voxels to millimeters
#Dimen is a list of [x, y, z] size of voxel
def vox_to_cm(voxCount, dimen):
	#Maybe check len(dimen) == 3
	voxVol = dimen[0] * dimen[1] * dimen[2]
	return voxCount * voxVol * 0.001

#Computes volumes of fat fraction, BAT and WAT
#Returns a list [(FFave, FFVol), (BATave, BATVol), (WATave, WATVol)]
def calc_fat_vol(slices, voxVol, BATlwr, BATupr, WATlwr, WATupr):
	#Get dimensions of each slice
	dimen = get_dimensions(slices[0])
	width = dimen[0]
	height = dimen[1]
	#Calc volumes of all segmented fat
	ff = count_voxels(slices, width, height, (BATlwr * 10), (WATupr * 10))
	ffVol = vox_to_cm(ff[0], voxVol)
	#Mask image for WAT and repeat calc
	wat = count_voxels(slices, width, height, (WATlwr * 10), (WATupr * 10))
	watVol = vox_to_cm(wat[0], voxVol)
	#Mask and repeat for BAT
	bat = count_voxels(slices, width, height, (BATlwr * 10), (BATupr * 10))
        batVol = vox_to_cm(bat[0], voxVol)
	return [(ff[1], ffVol),  (bat[1], batVol), (wat[1], watVol)]



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

name = ['FF %', 'FF Vol cm^3', 'BAT %', 'BAT Vol cm^3','WAT %', 'WAT Vol cm^3']
csvFile = open(dicomPath + "Fat_Fractions.csv", 'wb')
wr = csv.writer(csvFile)
wr.writerow(name)

slices = get_segmented_vox(dicomList, segment, width, height)
master = Tk()
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
