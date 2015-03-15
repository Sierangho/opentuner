// ADOBE SYSTEMS INCORPORATED
// Copyright  1993 - 2002 Adobe Systems Incorporated
// All Rights Reserved
//
// NOTICE:  Adobe permits you to use, modify, and distribute this 
// file in accordance with the terms of the Adobe license agreement
// accompanying it.  If you have received this file from a source
// other than Adobe, then your use, modification, or distribution
// of it requires the prior written permission of Adobe.
//-------------------------------------------------------------------------------


#define NOMINMAX
// project header files
#include "Dissolve.h"
#include "DissolveScripting.h"
#include "FilterBigDocument.h"
#include <time.h>
#include "Logger.h"
#include "Timer.h"
#include <stdio.h>
#include "halide_funcs.h"
#include <iostream>

#include "Halide.h"
#include <map>
#include <string>

extern "C" int halide_copy_to_host(void *user_context, buffer_t* buf);

//-------------------------------------------------------------------------------
// global variables
//-------------------------------------------------------------------------------
// parameters passed into PluginMain that need to be global to the project
FilterRecord * gFilterRecord = NULL;
intptr_t * gDataHandle = NULL;
int16 * gResult = NULL;		// all errors go here
SPBasicSuite * sSPBasic = NULL;

//-------------------------------------------------------------------------------
// local routines
//-------------------------------------------------------------------------------
// the six main routines of the plug in
void DoAbout(void);
void DoParameters(void);
void DoPrepare(void);
void DoStart(void);
void DoContinue(void);
void DoFinish(void);


void DoFilter(void);
void RefreshDirectory(void);
void WatchDirectory(void);
void TimeFilter(int, int);
//
//int main(int argc, char* argv[]) {
//	DoFilter();
//}

//-------------------------------------------------------------------------------
//
//	PluginMain
//	
//	All calls to the plug in module come through this routine.
//
//	Inputs:
//		const int16 selector		Host provides selector indicating what
//									command to do.
//
//	Inputs and Outputs:
//		FilterRecord *filterRecord	Host provides a pointer to parameter block
//									containing pertinent data and callbacks.
//									See PIFilter.h
//
//		intptr_t *data				Use this to store a handle or pointer to our global
//									data structure, which is maintained by the
//									host between calls to the plug in.
//
//	Outputs:
//		int16 *result				Returns error result. Some errors are handled
//									by the host, some are silent, and some you
//									must handle. See PIGeneral.h.
//
//-------------------------------------------------------------------------------
DLLExport MACPASCAL void PluginMain(const int16 selector,
								    FilterRecordPtr filterRecord,
								    intptr_t * data,
								    int16 * result)
{
	try {
	Logger logIt("Dissolve");
	logIt.Write( "Selector: ", false );
	logIt.Write( selector, true );

	// update our global parameters
	gFilterRecord = filterRecord;
	gResult = result;
	gDataHandle = data;

	if (selector == filterSelectorAbout)
	{
		sSPBasic = ((AboutRecord*)gFilterRecord)->sSPBasic;
	}
	else
	{
		sSPBasic = gFilterRecord->sSPBasic;

		if (gFilterRecord->bigDocumentData != NULL)
			gFilterRecord->bigDocumentData->PluginUsing32BitCoordinates = true;
	}

	// do the command according to the selector
	switch (selector)
	{
		case filterSelectorAbout:
			DoAbout();
			break;
		case filterSelectorParameters:
			DoParameters();
			break;
		case filterSelectorPrepare:
			DoPrepare();
			break;
		case filterSelectorStart:
			DoStart();
			break;
		case filterSelectorContinue:
			DoContinue();
			break;
		case filterSelectorFinish:
			DoFinish();
			break;
		default:
			break;
	}	
	
	} // end try

	catch (...)
	{
		if (NULL != result)
			*result = -1;
	}

}

void DoAbout(void)
{

}

//-------------------------------------------------------------------------------
//
// DoParameters
//-------------------------------------------------------------------------------
void DoParameters(void)
{
}



//-------------------------------------------------------------------------------
//
// DoPrepare 
//-------------------------------------------------------------------------------
void DoPrepare(void)
{
	// we don't need any buffer space
	// gFilterRecord->bufferSpace = 0; 

	// give as much memory back to Photoshop as you can
	// we only need a tile per plane plus the maskData
	// inTileHeight and inTileWidth are invalid at this
	// point. Assume the tile size is 256 max.
	VRect filterRect = GetFilterRect();
	int32 tileHeight = filterRect.bottom - filterRect.top;
	int32 tileWidth = filterRect.right - filterRect.left;
	if (tileHeight > 256)
		tileHeight = 256;
	if (tileWidth > 256)
		tileWidth = 256;
	int32 planes = gFilterRecord->planes;
	if (gFilterRecord->maskData != NULL)
		planes++;
	// duplicate because we have two copies, inData and outData
	planes *= 2;

	int32 totalSize = gFilterRecord->bigDocumentData->imageSize32.v * gFilterRecord->bigDocumentData->imageSize32.h * planes;
	// this is worst case and can be dropped considerably
	//if (gFilterRecord->maxSpace > totalSize)
	//	gFilterRecord->maxSpace = totalSize ;

	/*gFilterRecord->bigDocumentData->inRect32.top = -1;
	gFilterRecord->bigDocumentData->inRect32.left = -1;
	gFilterRecord->bigDocumentData->inRect32.bottom = gFilterRecord->bigDocumentData->imageSize32.v;
	gFilterRecord->bigDocumentData->inRect32.right = gFilterRecord->bigDocumentData->imageSize32.h;

	gFilterRecord->bigDocumentData->outRect32.top = 0;
	gFilterRecord->bigDocumentData->outRect32.left = 0;
	gFilterRecord->bigDocumentData->outRect32.bottom = gFilterRecord->bigDocumentData->imageSize32.v;
	gFilterRecord->bigDocumentData->outRect32.right = gFilterRecord->bigDocumentData->imageSize32.h;*/

	gFilterRecord->inputPadding = -1;

	gFilterRecord->advanceState();
	
	Logger logIt("dissolve");
	char stringVal[500];

	sprintf(stringVal, "max size - %d %d\n", gFilterRecord->maxSpace, gFilterRecord->inputPadding);
	logIt.Write(stringVal, true);
}



//-------------------------------------------------------------------------------
//
// DoStart
//
// The main filtering routine for this plug in. See if we have any registry
// parameters from the last time we ran. Determine if the UI needs to be
// displayed by reading the script parameters. Save the last dialog parameters
// in case something goes wrong or the user cancels.
//
//-------------------------------------------------------------------------------
void DoStart(void)
{
	DoFilter();
}



//-------------------------------------------------------------------------------
//
// DoContinue
//
// If we get here we probably did something wrong. This selector was needed
// before advanceState() was in the FilterRecord*. Now that we use advanceState()
// there is nothing for us to do but set all the rectangles to 0 and return.
//
//-------------------------------------------------------------------------------
void DoContinue(void)
{
	VRect zeroRect = { 0, 0, 0, 0 };

	SetInRect(zeroRect);
	SetOutRect(zeroRect);
	SetMaskRect(zeroRect);
}



//-------------------------------------------------------------------------------
//
// DoFinish
//
// Everything went as planned and the pixels have been modified. Now record
// scripting parameters and put our information in the Photoshop Registry for the
// next time we get called. The Registry saves us from keeping a preferences file.
//
//-------------------------------------------------------------------------------
void DoFinish(void)
{
	WriteScriptParameters();
}

void WatchDirectory()
{
	Logger logIt("Dissolve");
	Logger timing("Timing");
	DWORD dwWaitStatus;
	HANDLE dwChangeHandle;

	// Watch the directory for file creation and deletion. 
	dwChangeHandle = FindFirstChangeNotification(
		"C:/temp/plugin",                         // directory to watch 
		FALSE,                         // do not watch subtree 
		FILE_NOTIFY_CHANGE_LAST_WRITE); // watch file changes 

	if (dwChangeHandle == INVALID_HANDLE_VALUE)
	{
		timing.Write("\n ERROR: FindFirstChangeNotification function failed.\n", true);
		ExitProcess(GetLastError());
	}

	// Make a final validation check on our handles.
	if ((dwChangeHandle == NULL))
	{
		timing.Write("\n ERROR: Unexpected NULL from FindFirstChangeNotification.\n", true);
		ExitProcess(GetLastError());
	}
	//hack around double notify
	boolean second = false;
	
	// Change notification is set. Now wait on both notification 
	// handles and refresh accordingly. 
	while (TRUE)
	{
		// Wait for notification.

		timing.Write("\nWaiting for notification...\n");
		logIt.Write("WAITING FOR NOTIF", true);
		

		dwWaitStatus = WaitForSingleObject(dwChangeHandle, INFINITE);
		//logIt.Write("waitstatus received", true);

		switch (dwWaitStatus)
		{
		case WAIT_OBJECT_0:
			//logIt.Write("WAIT_OBJ_0", true);

			// A file was created, renamed, or deleted in the directory.
			// Refresh this directory and restart the notification.
			if (second){
				second = false;
				RefreshDirectory();
			}
			else{
				second = true;
			}
			if (FindNextChangeNotification(dwChangeHandle) == FALSE)
			{
				logIt.Write("FINDNEXT ERROR", true);

				printf("\n ERROR: FindNextChangeNotification function failed.\n");
				ExitProcess(GetLastError());
			}
			break;

		default:
			logIt.Write("UNHANDLED WAIT STATUS", true);

			printf("\n ERROR: Unhandled dwWaitStatus.\n");
			ExitProcess(GetLastError());
			break;
		}
	}
}

void RefreshDirectory()
{
	Logger timing("Timing");
	//read and parse file
	// create a file-reading object
	ifstream fin;
	fin.open("C:/temp/plugin/tileSize.txt"); // open a file
	if (!fin.good()){
		timing.Write("file not found", true);

		return; // exit if file not found
	}
	//timing.Write("parsing file", true);
	// read a single line for tile sizes. assume it has the right format
	std::string line;
	std::getline(fin, line);
	std::stringstream ss(line);
	int i;
	int counter = 0;
	std::vector<int> v;
	while (ss >> i){
		v.push_back(i);
		counter = counter + 1;
	}
	//timing.Write(counter);
	if (counter > 1){
		TimeFilter(v.at(0), v.at(1));
	}
}

void TimeFilter(int horSize, int verSize){
	Logger logIt("Dissolve");
	Logger timeIt("Timing");
	//logIt.Write("horTileSize: ");
	//logIt.Write(horSize, true);
	//logIt.Write("verTileSize: ");
	//logIt.Write(verSize, true);

	uint32_t horTileSize = (uint32_t) horSize;
	uint32_t verTileSize = (uint32_t) verSize;

	VRect filterRect = GetFilterRect();
	LARGE_INTEGER frequency, t1, t2;
	double mseconds;
	//number of times to repeat a run (should match runs length)
	double runs[35];
	int num_runs = 35;

	uint32_t imageWidth = filterRect.right;
	uint32_t imageHeight = filterRect.bottom;
	int32_t verPadding = 1;
	int32_t horPadding = 1;

	HINSTANCE hDLL = LoadLibrary("C:/temp/filter.dll");
	//standard
	typedef int(*filterFunc) (buffer_t *, buffer_t *);
	//irfanblur
	//typedef int(*filterFunc) (double, double, double, double, buffer_t *, buffer_t *);
	//irfansharpen
	//typedef int(*filterFunc) (double, double, buffer_t *, buffer_t *);
	//threshold
	//typedef int(*filterFunc) (uint8_t, buffer_t *, buffer_t *, buffer_t *, buffer_t *);
	filterFunc apply_filter = (filterFunc)GetProcAddress(hDLL, "halide_out");

	if (hDLL != NULL)
	{
		if (!apply_filter)
		{
			logIt.Write("not applied filter", true);
		}
	}
	else{
		logIt.Write("null");
	}
	
	uint32_t horTiles = (uint32_t)ceil(filterRect.right / (double)horTileSize);
	uint32_t verTiles = (uint32_t)ceil(filterRect.bottom / (double)verTileSize);

	for (int i = 0; i < num_runs; i++){
		//store time
		QueryPerformanceFrequency(&frequency);
		QueryPerformanceCounter(&t1);

		// Fixed numbers are 16.16 
		// the first 16 bits represent the whole number
		// the last 16 bits represent the fraction
		gFilterRecord->inputRate = (int32)1 << 16;
		gFilterRecord->maskRate = (int32)1 << 16;

		/*logIt.Write("horizontal tiles:");
		logIt.Write((int32)horTiles);
		logIt.Write(" vertical tiles:");
		logIt.Write((int32)verTiles, true);
*/
		for (int32 y = 0; y < verTiles; y++){
			for (int32 x = 0; x < horTiles; x++){

				VRect inRect;
				inRect.top = y * verTileSize - verPadding;
				inRect.bottom = y * verTileSize + verTileSize + verPadding;
				inRect.left = x * horTileSize - horPadding;
				inRect.right = x * horTileSize + horTileSize + horPadding;

				if (inRect.right > imageWidth + horPadding) inRect.right = imageWidth + horPadding;
				if (inRect.bottom > imageHeight + verPadding) inRect.bottom = imageHeight + verPadding;

				VRect outRect;
				outRect.top = y * verTileSize;
				outRect.bottom = y * verTileSize + verTileSize;
				outRect.left = x * horTileSize;
				outRect.right = x * horTileSize + horTileSize;

				if (outRect.bottom > imageHeight) outRect.bottom = imageHeight;
				if (outRect.right > imageWidth) outRect.right = imageWidth;

				SetInRect(inRect);
				SetOutRect(outRect);
				gFilterRecord->inputPadding = -1;
				//gFilterRecord->outputPadding = 1;
				
				///////////////THRESHOLD STUFF
				//buffer_t * r_buf = (buffer_t *)malloc(sizeof(buffer_t));
				//buffer_t * g_buf = (buffer_t *)malloc(sizeof(buffer_t));
				//buffer_t * b_buf = (buffer_t *)malloc(sizeof(buffer_t));

				//gFilterRecord->outLoPlane = gFilterRecord->inLoPlane = (int16)0; gFilterRecord->outHiPlane = gFilterRecord->inHiPlane = (int16)2;
				// update the gFilterRecord with our latest request
				//*gResult = gFilterRecord->advanceState();
				//if (*gResult != noErr) return;
				//uint8_t * bytes = (uint8_t *)gFilterRecord->inData;
				//uint32_t input_width = inRect.right - inRect.left; uint32_t input_height = inRect.bottom - inRect.top;
				//uint32_t input_scanline = gFilterRecord->inRowBytes;
				///*prepare the buffer_t*/
				//r_buf->extent[0] = input_width; r_buf->extent[1] = input_height; r_buf->extent[2] = 0; r_buf->extent[3] = 0;
				//r_buf->stride[0] = 3; r_buf->stride[1] = input_scanline; r_buf->stride[2] = 0; r_buf->stride[3] = 0;
				//r_buf->min[0] = 0; r_buf->min[1] = 0; r_buf->min[2] = 0; r_buf->min[3] = 0;
				//r_buf->elem_size = 1;
				//r_buf->host = (uint8_t *)(uint32_t)gFilterRecord->inData;
				//r_buf->host_dirty = 0; r_buf->dev_dirty = 0; r_buf->dev = 0;

				//g_buf->extent[0] = input_width; g_buf->extent[1] = input_height; g_buf->extent[2] = 0; g_buf->extent[3] = 0;
				//g_buf->stride[0] = 3; g_buf->stride[1] = input_scanline; g_buf->stride[2] = 0; g_buf->stride[3] = 0;
				//g_buf->min[0] = 0; g_buf->min[1] = 0; g_buf->min[2] = 0; g_buf->min[3] = 0;
				//g_buf->elem_size = 1;
				//g_buf->host = (uint8_t *)((uint32_t)gFilterRecord->inData + 1);
				//g_buf->host_dirty = 0; g_buf->dev_dirty = 0; g_buf->dev = 0;

				///*prepare the buffer_t*/
				//b_buf->extent[0] = input_width; b_buf->extent[1] = input_height; b_buf->extent[2] = 0; b_buf->extent[3] = 0;
				//b_buf->stride[0] = 3; b_buf->stride[1] = input_scanline; b_buf->stride[2] = 0; b_buf->stride[3] = 0;
				//b_buf->min[0] = 0; b_buf->min[1] = 0; b_buf->min[2] = 0; b_buf->min[3] = 0;
				//b_buf->elem_size = 1;
				//b_buf->host = (uint8_t *)((uint32_t)gFilterRecord->inData + 2);
				//b_buf->host_dirty = 0; b_buf->dev_dirty = 0; b_buf->dev = 0;

				//buffer_t * output_buf = (buffer_t *)malloc(sizeof(buffer_t));
				//uint32_t output_width = outRect.right - outRect.left; uint32_t output_height = outRect.bottom - outRect.top; uint32_t output_scanline = gFilterRecord->outRowBytes;
				//output_buf->extent[0] = output_width; output_buf->extent[1] = output_height; output_buf->extent[2] = 0; output_buf->extent[3] = 0;
				//output_buf->stride[0] = 3; output_buf->stride[1] = output_scanline; output_buf->stride[2] = 0; output_buf->stride[3] = 0;
				//output_buf->min[0] = 0; output_buf->min[1] = 0; output_buf->min[2] = 0; output_buf->min[3] = 0;
				//output_buf->elem_size = 1;
				//output_buf->host = (uint8_t *)(uint32_t)gFilterRecord->outData;
				//output_buf->host_dirty = 0; output_buf->dev_dirty = 0; output_buf->dev = 0;

				//uint8_t threshold = 125;
				//int ret_code = apply_filter(threshold, g_buf, b_buf, r_buf, output_buf);
				//output_buf->host = (uint8_t *)((uint32_t)gFilterRecord->outData + 1);
				//ret_code = apply_filter(threshold, g_buf, b_buf, r_buf, output_buf);
				//output_buf->host = (uint8_t *)((uint32_t)gFilterRecord->outData + 2);
				//ret_code = apply_filter(threshold, g_buf, b_buf, r_buf, output_buf);
				//////////THRESHOLD STUFF

				//////////IRFANVIEW STUFF
//				gFilterRecord->outLoPlane = gFilterRecord->inLoPlane = 0;
//				gFilterRecord->outHiPlane = gFilterRecord->inHiPlane = 2;
//				// update the gFilterRecord with our latest request
//				*gResult = gFilterRecord->advanceState();
//				if (*gResult != noErr) return;
//				
//				uint8_t * bytes = (uint8_t *)gFilterRecord->inData;
//				
//				uint32_t output_width = outRect.right - outRect.left;
//				uint32_t output_height = outRect.bottom - outRect.top;
//				uint32_t input_width = inRect.right - inRect.left;
//				uint32_t input_height = inRect.bottom - inRect.top;
//				
//				uint32_t output_scanline = gFilterRecord->outRowBytes;
//				uint32_t input_scanline = gFilterRecord->inRowBytes;
//				
//				/*logIt.Write("output bytes: ");
//				logIt.Write((int32)output_scanline, true);
//*/
//				/*prepare the buffer_t*/
//				buffer_t * input_buf = (buffer_t *)malloc(sizeof(buffer_t));
//				buffer_t * output_buf = (buffer_t *)malloc(sizeof(buffer_t));
//				
//				input_buf->extent[0] = 3; input_buf->extent[1] = input_width; input_buf->extent[2] = input_height; input_buf->extent[3] = 0;
//				input_buf->stride[0] = 1; input_buf->stride[1] = 3; input_buf->stride[2] = input_scanline; input_buf->stride[3] = 0;
//				input_buf->min[0] = 0; input_buf->min[1] = 0; input_buf->min[2] = 0; input_buf->min[3] = 0;
//				input_buf->elem_size = 1;
//				input_buf->host = (uint8_t *)(uint32_t)gFilterRecord->inData;
//				input_buf->host_dirty = 0;
//				input_buf->dev_dirty = 0;
//				input_buf->dev = 0;
//
//				output_buf->extent[0] = 3; output_buf->extent[1] = output_width; output_buf->extent[2] = output_height; output_buf->extent[3] = 0;
//				output_buf->stride[0] = 1; output_buf->stride[1] = 3; output_buf->stride[2] = output_scanline; output_buf->stride[3] = 0;
//				output_buf->min[0] = 0; output_buf->min[1] = 0; output_buf->min[2] = 0; output_buf->min[3] = 0;
//				output_buf->elem_size = 1;
//				output_buf->host = (uint8_t *)(uint32_t)gFilterRecord->outData;
//				output_buf->host_dirty = 0;
//				output_buf->dev_dirty = 0;
//				output_buf->dev = 0;
//				/* end preparing buffer_t*/
//				
//				//BLUR
//				//double p1 = 33;
//				//double in1 = 1.0;
//				//double in2 = 0.01;
//				//double in3 = 0.125;
//				//int ret_code = apply_filter(p1, in1, in2, in3, input_buf, output_buf);
//				//SHARPEN
//				double p1 = 20;
//				double in1 = 0.005;
//				//int ret_code = apply_filter(p1, in1, input_buf, output_buf);
//				////////////END RIFANVIEW STUFF
//


				for (int16 plane = 0; plane < gFilterRecord->planes; plane++)
				{
					// we want one plane at a time, small memory foot print is good
					gFilterRecord->outLoPlane = gFilterRecord->inLoPlane = plane;
					gFilterRecord->outHiPlane = gFilterRecord->inHiPlane = plane;
					// update the gFilterRecord with our latest request
					*gResult = gFilterRecord->advanceState();
					if (*gResult != noErr) return;

					uint8_t * bytes = (uint8_t *)gFilterRecord->inData;

					uint32_t output_width = outRect.right - outRect.left;
					uint32_t output_height = outRect.bottom - outRect.top;
					uint32_t input_width = inRect.right - inRect.left;
					uint32_t input_height = inRect.bottom - inRect.top;

					uint32_t output_scanline = gFilterRecord->outRowBytes;
					uint32_t input_scanline = gFilterRecord->inRowBytes;

					/*logIt.Write("output bytes: ");
					logIt.Write((int32)output_scanline, true);
*/
					/*prepare the buffer_t*/
					buffer_t * input_buf = (buffer_t *)malloc(sizeof(buffer_t));
					buffer_t * output_buf = (buffer_t *)malloc(sizeof(buffer_t));

					input_buf->extent[0] = input_width; input_buf->extent[1] = input_height; input_buf->extent[2] = 0; input_buf->extent[3] = 0;
					input_buf->stride[0] = 1; input_buf->stride[1] = input_scanline; input_buf->stride[2] = 0; input_buf->stride[3] = 0;
					input_buf->min[0] = 0; input_buf->min[1] = 0; input_buf->min[2] = 0; input_buf->min[3] = 0;
					input_buf->elem_size = 1;
					input_buf->host = (uint8_t *)(uint32_t)gFilterRecord->inData;
					input_buf->host_dirty = 1;
					input_buf->dev_dirty = 0;
					input_buf->dev = 0;

					output_buf->extent[0] = output_width; output_buf->extent[1] = output_height; output_buf->extent[2] = 0; output_buf->extent[3] = 0;
					output_buf->stride[0] = 1; output_buf->stride[1] = output_scanline; output_buf->stride[2] = 0; output_buf->stride[3] = 0;
					output_buf->min[0] = 0; output_buf->min[1] = 0; output_buf->min[2] = 0; output_buf->min[3] = 0;
					output_buf->elem_size = 1;
					output_buf->host = (uint8_t *)(uint32_t)gFilterRecord->outData;
					output_buf->host_dirty = 0;
					output_buf->dev_dirty = 0;
					output_buf->dev = 0;
					/* end preparing buffer_t*/

					//logIt.Write("prepared buffer_ts ", true);

					//uint8_t threshold = 125;
					//int ret_code = apply_filter(threshold, input_buf, input_buf, input_buf, output_buf);
					int ret_code = apply_filter(input_buf, output_buf);
					//logIt.Write("return code: ");
					//logIt.Write(ret_code, true);
					//logIt.Write("applied filter", true);
				}
			}
		}

		QueryPerformanceCounter(&t2);
		mseconds = (t2.QuadPart - t1.QuadPart) * 1000.0 / frequency.QuadPart;
		runs[i] = mseconds;

		ofstream myfile;
		myfile.open("C:/temp/result/result.txt");

		myfile << "";
		myfile.close();
	}

	logIt.Write("finished runs", true);

	//calc mean and std dev
	double mean = 0;
	double dev = 0;
	for (int i = 0; i < num_runs; i++){
		mean += runs[i];
	}
	mean = mean / num_runs;

	for (int i = 0; i < num_runs; i++){
		dev += (runs[i] - mean)*(runs[i] - mean);
	}

	dev = sqrt(dev / num_runs);

	FreeLibrary(hDLL);
	//logIt.Write("freed library", true);
	//logIt.Write("Filter was not applied", true);
	logIt.Write(mean, true);
	logIt.Write(dev, true);
	for (int i = 0; i < num_runs; i++){
		logIt.Write(runs[i]);
		logIt.Write(" ");
	}
	logIt.Write("\n", true);

	ofstream myfile;
	myfile.open("C:/temp/result/result.txt");

	myfile << mean;
	myfile.close();
	//logIt.Write("wrote file", true);

}

//-------------------------------------------------------------------------------
//
// DoFilter
// Hijack and do open tuner stuff
// We do this a tile at a time making sure the rect.
// we ask for is in the bounds of the filterRect.
//
//-------------------------------------------------------------------------------
void DoFilter(void)
{
	// //notify that the plugin has started
	//ofstream myfile;
	//myfile.open("C:/temp/result/result.txt");
	//myfile << 1000;
	//myfile.close();

	//WatchDirectory();
	//

	////// TESTING CODE to run a single time
	//Logger logIt("Dissolve");
	//Logger timeIt("Timing");

	VRect filterRect = GetFilterRect();
	LARGE_INTEGER frequency, t1, t2;
	double mseconds;
	//number of times to repeat a run (should match runs length)
	double runs[1];
	int num_runs = 1;

	uint32_t imageWidth = filterRect.right;
	uint32_t imageHeight = filterRect.bottom;
	int32_t verPadding = 1;
	int32_t horPadding = 1;

	
	/* BEGIN LOOP */
	
	////loop the tile size////////////
	//int step = 528;
	//for (int horSize = 1;horSize <= ceil(imageWidth / (double)step); horSize++){
	//	for (int verSize = 1; verSize <= ceil(imageHeight / (double)step); verSize++){
	//		uint32_t horTileSize = (uint32_t)(horSize*step);
	//		uint32_t verTileSize = (uint32_t)(verSize*step);
	/////////////////////////////////////

	//load dll TODO make a variable
//	HINSTANCE hDLL = LoadLibrary("C:/adobe/blur.dll");
	HINSTANCE hDLL = LoadLibrary("C:/temp/filter.dll");
	
	//standard
	typedef int(*filterFunc) (buffer_t *, buffer_t *);
	//irfanblur
	//typedef int(*filterFunc) (double, double, double, double, buffer_t *, buffer_t *);
	//irfansharpen
	//typedef int(*filterFunc) (double, double, buffer_t *, buffer_t *);
	//threshold
	//typedef int(*filterFunc) (uint8_t, buffer_t *, buffer_t *, buffer_t *, buffer_t *);
	
	filterFunc apply_filter = (filterFunc)GetProcAddress(hDLL, "halide_out");

	uint32_t horTileSize = 4000;
	uint32_t verTileSize = 528;

	uint32_t horTiles = (uint32_t)ceil(filterRect.right / (double)horTileSize);
	uint32_t verTiles = (uint32_t)ceil(filterRect.bottom / (double)verTileSize);

	for (int i = 0; i < num_runs; i++){
		QueryPerformanceFrequency(&frequency);
		QueryPerformanceCounter(&t1);

		gFilterRecord->inputRate = (int32)1 << 16;
		gFilterRecord->maskRate = (int32)1 << 16;

		for (int32 y = 0; y < verTiles; y++){
			for (int32 x = 0; x < horTiles; x++){

				VRect inRect;
				inRect.top = y * verTileSize - verPadding;
				inRect.bottom = y * verTileSize + verTileSize + verPadding;
				inRect.left = x * horTileSize - horPadding;
				inRect.right = x * horTileSize + horTileSize + horPadding;

				if (inRect.right > imageWidth + horPadding) inRect.right = imageWidth + horPadding;
				if (inRect.bottom > imageHeight + verPadding) inRect.bottom = imageHeight + verPadding;

				VRect outRect; // added -1 for irfanview stuff
				outRect.top = y * verTileSize;
				outRect.bottom = y * verTileSize + verTileSize;
				outRect.left = x * horTileSize;
				outRect.right = x * horTileSize + horTileSize;

				if (outRect.bottom > imageHeight) outRect.bottom = imageHeight;
				if (outRect.right > imageWidth) outRect.right = imageWidth;

				SetInRect(inRect);
				SetOutRect(outRect);
				gFilterRecord->inputPadding = -1;
				//gFilterRecord->outputPadding = 1;
				///////////////////////THRESHOLD STUFF
				////get plane buffer T's for threshold
				//buffer_t * r_buf = (buffer_t *)malloc(sizeof(buffer_t));
				//buffer_t * g_buf = (buffer_t *)malloc(sizeof(buffer_t));
				//buffer_t * b_buf = (buffer_t *)malloc(sizeof(buffer_t));
				//
				//gFilterRecord->outLoPlane = gFilterRecord->inLoPlane = (int16) 0; gFilterRecord->outHiPlane = gFilterRecord->inHiPlane = (int16) 2;
				//// update the gFilterRecord with our latest request
				//*gResult = gFilterRecord->advanceState();
				//if (*gResult != noErr) return;
				//uint8_t * bytes = (uint8_t *)gFilterRecord->inData;
				//uint32_t input_width = inRect.right - inRect.left; uint32_t input_height = inRect.bottom - inRect.top; 
				//uint32_t input_scanline = gFilterRecord->inRowBytes;
				///*prepare the buffer_t*/
				//r_buf->extent[0] = input_width; r_buf->extent[1] = input_height; r_buf->extent[2] = 0; r_buf->extent[3] = 0;
				//r_buf->stride[0] = 3; r_buf->stride[1] = input_scanline; r_buf->stride[2] = 0; r_buf->stride[3] = 0;
				//r_buf->min[0] = 0; r_buf->min[1] = 0; r_buf->min[2] = 0; r_buf->min[3] = 0;
				//r_buf->elem_size = 1;
				//r_buf->host = (uint8_t *)(uint32_t)gFilterRecord->inData;
				//r_buf->host_dirty = 0; r_buf->dev_dirty = 0; r_buf->dev = 0;

				//g_buf->extent[0] = input_width; g_buf->extent[1] = input_height; g_buf->extent[2] = 0; g_buf->extent[3] = 0;
				//g_buf->stride[0] = 3; g_buf->stride[1] = input_scanline; g_buf->stride[2] = 0; g_buf->stride[3] = 0;
				//g_buf->min[0] = 0; g_buf->min[1] = 0; g_buf->min[2] = 0; g_buf->min[3] = 0;
				//g_buf->elem_size = 1;
				//g_buf->host = (uint8_t *)((uint32_t)gFilterRecord->inData + 1);
				//g_buf->host_dirty = 0; g_buf->dev_dirty = 0; g_buf->dev = 0;
				//			
				///*prepare the buffer_t*/
				//b_buf->extent[0] = input_width; b_buf->extent[1] = input_height; b_buf->extent[2] = 0; b_buf->extent[3] = 0;
				//b_buf->stride[0] = 3; b_buf->stride[1] = input_scanline; b_buf->stride[2] = 0; b_buf->stride[3] = 0;
				//b_buf->min[0] = 0; b_buf->min[1] = 0; b_buf->min[2] = 0; b_buf->min[3] = 0;
				//b_buf->elem_size = 1;
				//b_buf->host = (uint8_t *)((uint32_t)gFilterRecord->inData + 2);
				//b_buf->host_dirty = 0; b_buf->dev_dirty = 0; b_buf->dev = 0;

				//buffer_t * output_buf = (buffer_t *)malloc(sizeof(buffer_t));
				//uint32_t output_width = outRect.right - outRect.left; uint32_t output_height = outRect.bottom - outRect.top; uint32_t output_scanline = gFilterRecord->outRowBytes;
				//output_buf->extent[0] = output_width; output_buf->extent[1] = output_height; output_buf->extent[2] = 0; output_buf->extent[3] = 0;
				//output_buf->stride[0] = 3; output_buf->stride[1] = output_scanline; output_buf->stride[2] = 0; output_buf->stride[3] = 0;
				//output_buf->min[0] = 0; output_buf->min[1] = 0; output_buf->min[2] = 0; output_buf->min[3] = 0;
				//output_buf->elem_size = 1;
				//output_buf->host = (uint8_t *)(uint32_t)gFilterRecord->outData;
				//output_buf->host_dirty = 0; output_buf->dev_dirty = 0; output_buf->dev = 0;

				//uint8_t threshold = 125;
				//int ret_code = apply_filter(threshold, g_buf, b_buf, r_buf, output_buf);
				//output_buf->host = (uint8_t *)((uint32_t)gFilterRecord->outData+1);
				//ret_code = apply_filter(threshold, g_buf, b_buf, r_buf, output_buf);
				//output_buf->host = (uint8_t *)((uint32_t)gFilterRecord->outData+2);
				//ret_code = apply_filter(threshold, g_buf, b_buf, r_buf, output_buf);

//
//				//////////////////END THRESHOLD


				//////////IRFANVIEW STUFF
				//gFilterRecord->outLoPlane = gFilterRecord->inLoPlane = 0;
				//gFilterRecord->outHiPlane = gFilterRecord->inHiPlane = 2;
				//// update the gFilterRecord with our latest request
				//*gResult = gFilterRecord->advanceState();
				//if (*gResult != noErr) return;

				//uint8_t * bytes = (uint8_t *)gFilterRecord->inData;

				//uint32_t output_width = outRect.right - outRect.left;
				//uint32_t output_height = outRect.bottom - outRect.top;
				//uint32_t input_width = inRect.right - inRect.left;
				//uint32_t input_height = inRect.bottom - inRect.top;

				//uint32_t output_scanline = gFilterRecord->outRowBytes;
				//uint32_t input_scanline = gFilterRecord->inRowBytes;

				///*logIt.Write("output bytes: ");
				//logIt.Write((int32)output_scanline, true);
				//*/
				///*prepare the buffer_t*/
				//buffer_t * input_buf = (buffer_t *)malloc(sizeof(buffer_t));
				//buffer_t * output_buf = (buffer_t *)malloc(sizeof(buffer_t));

				//input_buf->extent[0] = 3; input_buf->extent[1] = input_width; input_buf->extent[2] = input_height; input_buf->extent[3] = 0;
				//input_buf->stride[0] = 1; input_buf->stride[1] = 3; input_buf->stride[2] = input_scanline; input_buf->stride[3] = 0;
				//input_buf->min[0] = 0; input_buf->min[1] = 0; input_buf->min[2] = 0; input_buf->min[3] = 0;
				//input_buf->elem_size = 1;
				//input_buf->host = (uint8_t *)(uint32_t)gFilterRecord->inData;
				//input_buf->host_dirty = 0;
				//input_buf->dev_dirty = 0;
				//input_buf->dev = 0;

				//output_buf->extent[0] = 3; output_buf->extent[1] = output_width; output_buf->extent[2] = output_height; output_buf->extent[3] = 0;
				//output_buf->stride[0] = 1; output_buf->stride[1] = 3; output_buf->stride[2] = output_scanline; output_buf->stride[3] = 0;
				//output_buf->min[0] = 0; output_buf->min[1] = 0; output_buf->min[2] = 0; output_buf->min[3] = 0;
				//output_buf->elem_size = 1;
				//output_buf->host = (uint8_t *)(uint32_t)gFilterRecord->outData;
				//output_buf->host_dirty = 0;
				//output_buf->dev_dirty = 0;
				//output_buf->dev = 0;
				///* end preparing buffer_t*/

				////BLUR
				////double p1 = 33;
				////double in1 = 1.0;
				////double in2 = 0.01;
				////double in3 = 0.125;
				////int ret_code = apply_filter(p1, in1, in2, in3, input_buf, output_buf);
				////SHARPEN
				//double p1 = 20;
				//double in1 = 0.005;
				//int ret_code = apply_filter(p1, in1, input_buf, output_buf);
				//////////////END RIFANVIEW STUFF


				//NORMAL OPERATION
				for (int16 plane = 0; plane < gFilterRecord->planes; plane++)
				{
					// we want one plane at a time, small memory foot print is good
					gFilterRecord->outLoPlane = gFilterRecord->inLoPlane = plane;
					gFilterRecord->outHiPlane = gFilterRecord->inHiPlane = plane;
					// update the gFilterRecord with our latest request
					*gResult = gFilterRecord->advanceState();
					if (*gResult != noErr) return;

					uint8_t * bytes = (uint8_t *)gFilterRecord->inData;

					uint32_t output_width = outRect.right - outRect.left;
					uint32_t output_height = outRect.bottom - outRect.top;
					uint32_t input_width = inRect.right - inRect.left;
					uint32_t input_height = inRect.bottom - inRect.top;

					uint32_t output_scanline = gFilterRecord->outRowBytes;
					uint32_t input_scanline = gFilterRecord->inRowBytes;

					/*prepare the buffer_t*/
					buffer_t * input_buf = (buffer_t *)malloc(sizeof(buffer_t));
					buffer_t * output_buf = (buffer_t *)malloc(sizeof(buffer_t));

					input_buf->extent[0] = input_width; input_buf->extent[1] = input_height; input_buf->extent[2] = 0; input_buf->extent[3] = 0;
					input_buf->stride[0] = 1; input_buf->stride[1] = input_scanline; input_buf->stride[2] = 0; input_buf->stride[3] = 0;
					input_buf->min[0] = 0; input_buf->min[1] = 0; input_buf->min[2] = 0; input_buf->min[3] = 0;
					input_buf->elem_size = 1;
					input_buf->host = (uint8_t *)(uint32_t)gFilterRecord->inData;
					input_buf->host_dirty = 1;
					input_buf->dev_dirty = 0;
					input_buf->dev = 0;

					output_buf->extent[0] = output_width; output_buf->extent[1] = output_height; output_buf->extent[2] = 0; output_buf->extent[3] = 0;
					output_buf->stride[0] = 1; output_buf->stride[1] = output_scanline; output_buf->stride[2] = 0; output_buf->stride[3] = 0;
					output_buf->min[0] = 0; output_buf->min[1] = 0; output_buf->min[2] = 0; output_buf->min[3] = 0;
					output_buf->elem_size = 1;
					output_buf->host = (uint8_t *)(uint32_t)gFilterRecord->outData;
					output_buf->host_dirty = 0;
					output_buf->dev_dirty = 1;
					output_buf->dev = 0;
					/* end preparing buffer_t*/
					uint8_t * dst = (uint8_t *)gFilterRecord->outData;
					for (int i = 0; i < output_scanline*output_height; i++){
						dst[i] = 255;
					}
					//int ret_code = apply_filter(150, input_buf, input_buf, input_buf, output_buf);
					int ret_code = apply_filter(input_buf, output_buf);
					halide_copy_to_host(NULL, output_buf);
	/*				logIt.Write("return code: ");
					logIt.Write(ret_code, true);
					logIt.Write("applied filter", true);
	*/			}
			}
		}

		QueryPerformanceCounter(&t2);
		mseconds = (t2.QuadPart - t1.QuadPart) * 1000.0 / frequency.QuadPart;
		runs[i] = mseconds;
	}


	////calc mean and std dev
	//double dev = 0;
	//double mean = 0;
	//for (int i = 0; i < num_runs; i++){
	//	mean += runs[i];
	//}
	//mean = mean / num_runs;
	//for (int i = 0; i < num_runs; i++){
	//	dev += (runs[i] - mean)*(runs[i] - mean);
	//}

	//dev = dev / num_runs;

	//ostringstream oss;
	//oss << horTileSize << " " << verTileSize << " " << mean << " " << dev << "\n";
	/*timeIt.Write((int32) horTileSize, false);
	timeIt.Write(" ");
	timeIt.Write((int32)verTileSize);
	timeIt.Write(" ");*/
	//timeIt.Write(mean);
	/*timeIt.Write(" ");
	timeIt.Write(dev, true);
*/
	///////// loop the tile size
	//	}
	//}
	////////
	FreeLibrary(hDLL);
}

// end Dissolve.cpp