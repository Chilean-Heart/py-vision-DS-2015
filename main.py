import cv2
import numpy as np
from networktables import NetworkTable


def main():
    #Constants

    kCamPort = 1
    kFrameInterval = 50

    kMinHsv = 19
    kMaxHsv = 33
    kBMinHsv = 0
    kBMaxHsv = 180

    kBotWidth = 360
    kTopWidth = 430
    kHeight = 320
    kCamHeight = 33
    kFocalLength = 4
    kSensorHeight = 3.6
    kSensorWidth = 4.8
    kFieldView = 60

    kFrameWidth = 320
    kFrameHeight = 240

    kXString = "X"
    kYString = "Y"
    kNewCentroidString = "centroid_new"
    kDistString = "dist"
    kRatioXYString = "ratio_xy"
    kRatioYXString = "ratio_yx"

    kMatrixData = [[313, 146, 50], [258, 138, 60], [222, 132, 70], [192, 130, 80],
                   [171, 127, 90], [154, 106, 100], [140, 98, 110], [130, 95, 120],
                   [120, 90, 130], [112, 84, 140], [105, 78, 150], [98, 75, 160],
                   [94, 73, 170], [89, 70, 180], [81, 60, 200], [45, 36, 300]]
    kDataAmount = len(kMatrixData)

    #Debugging and tests
    debug = False
    useGUI = True
    useLocalRobot = True

    #Cam variables
    ret = False
    camClosed = True
    isConnected = False

    #Robot Variables
    robotIP = '10.25.76.2'
    localIP = '127.0.0.1'
    table = None
    centroid_is_new = False

    #Counting pixels
    x_count = 0
    y_count = 0
    dist_index = 42
    distance = 0

    #HSV Values
    yellow_min = np.array([kMinHsv, 50, 50], np.uint8)
    yellow_max = np.array([kMaxHsv, 255, 255], np.uint8)
    black_min = np.array([kBMinHsv, 50, 50], np.uint8)
    black_max = np.array([kBMaxHsv, 255, 255], np.uint8)

    #Function Parameters
    se = cv2.getStructuringElement(cv2.MORPH_RECT, (4,4))
    center = (kFrameWidth / 2, kFrameHeight / 2)

    #Network table. Startup and object creation
    if useLocalRobot:
        NetworkTable.setIPAddress(localIP)
    else:
        NetworkTable.setIPAddress(robotIP)
    NetworkTable.setClientMode()
    NetworkTable.initialize()
    if useLocalRobot:
        table = NetworkTable.getTable("data_table")
    else:
        table = NetworkTable.getTable("vision")

    #Camera creation and parameters
    cam = cv2.VideoCapture(kCamPort)
    cam.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, kFrameWidth)
    cam.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, kFrameHeight)

    #CV Named window
    cv2.namedWindow("Window", 1)

    #Function to connect to data table
    def connect():
        global isConnected
        isConnected = False
        while not isConnected:
            try:
                isConnected = table.getBoolean("connection_state")
            except KeyError as err:
                isConnected = False

    #Startup Camera
    while camClosed:
        if cam.isOpened():
            ret, img = cam.read()
            camClosed = not ret
        else:
            camClosed = True

    connect()

    #Endless loop to read and process frames
    while ret:
        #Image conversion
        hsv_image = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        #black_detect_image = hsv_image

        #black_threshold_image = cv2.inRange(black_detect_image, black_min, black_max)
        threshold_image = cv2.inRange(hsv_image, yellow_min, yellow_max)

        open_morph_image = cv2.morphologyEx(threshold_image, cv2.MORPH_OPEN, se)
        close_morph_image = cv2.morphologyEx(open_morph_image, cv2.MORPH_CLOSE, se)
        blurred_image = cv2.GaussianBlur(close_morph_image, (0,0), 5)


        edges_image = cv2.Canny(blurred_image, 100, 255)


        contour_image = edges_image.copy()
        contours, hierarchy = cv2.findContours(contour_image, cv2.cv.CV_RETR_EXTERNAL, cv2.cv.CV_CHAIN_APPROX_SIMPLE)
        areas = [cv2.contourArea(c) for c in contours]

        try:
            max_index = np.argmax(areas)
        except ValueError as err:
            max_index = 0

        if max_index != 0:
            cnt = contours[max_index]
            x,y,w,h = cv2.boundingRect(cnt)
            cv2.rectangle(blurred_image, (x,y), (x+w, y+h), (255, 255, 255), 2)

        #Obtain moments
        moments = cv2.moments(blurred_image, True)

        try:
            #Calculate centroid based on moments
            center = (int(moments['m10'] / moments['m00']), int(moments['m01'] / moments['m00']))
            centroid_is_new = True
        except ZeroDivisionError as err:
            #Deal with m00 == 0
            centroid_is_new = False
            print(err.args)
            print("Couldn't find moments")

        for i in range(kFrameWidth):
            x_count += blurred_image[center[1], i]
        x_count /= 255

        for j in range(kFrameHeight):
            y_count += blurred_image[j, center[0]]
        y_count /= 255

        if x_count < 30:
            dist_index = 42
        else:
            for i in range(len(kMatrixData)):
                try:
                    avgr = (kMatrixData[i][0] + kMatrixData[i + 1][0]) / 2.0
                except IndexError as err:
                    avgr = kMatrixData[i][0]
                if x_count >= (avgr):
                    dist_index = i
                    break
                i += 1

        if dist_index is 42:
            distance = 0
        elif dist_index < (kDataAmount):
            distance = kMatrixData[dist_index][2]

        ratioXY = x_count / y_count
        ratioYX = y_count / x_count

        #Draw circle to mark centroid
        if useGUI:
            cv2.circle(img=blurred_image, center=center, radius=4, color=(0, 0, 0), thickness=-2)
            #Draw image on window
            cv2.imshow("Window", blurred_image)

        #Attempt to write values on NetworkTables
        try:
            table.putNumber(kXString, center[0])
            table.putNumber(kYString, center[1])
            table.putBoolean(kNewCentroidString, centroid_is_new)
            table.putNumber(kDistString, distance)
            table.putNumber(kRatioXYString, ratioXY)
            table.putNumber(kRatioYXString, ratioYX)
        except KeyError as err:
            print(err.args)
            print("Couldn't upload values")
            isConnected = False

        #Print center point value to std.out
        if useLocalRobot:
            print(center)
            print(distance)
            print(x_count)
            print(y_count)

        #Read next image frame
        ret, img = cam.read()

        #Reconnect to server
        if not isConnected:
            connect()

        #Mandatory frame delay
        if cv2.waitKey(kFrameInterval) == 27:
            break


if __name__ == '__main__':
    main()
    cv2.destroyAllWindows()
    exit(0)
