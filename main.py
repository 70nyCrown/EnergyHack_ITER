class InputData:

    #Класс входных данных для района Москвы
    #Информация о резерве мощности https://utp.rossetimr.ru/map-epc?roistat_visit=228566
    #Информация о количестве парковок, АЗС, ТЦ, МКД https://openstreetmap.ru/?roistat_visit=228566#map=13/55.7577/37.6568
    #Информация о населении, плотности населения, площади тестового района 1 https://ru.wikipedia.org/wiki/%D0%9B%D0%B5%D1%84%D0%BE%D1%80%D1%82%D0%BE%D0%B2%D0%BE_(%D1%80%D0%B0%D0%B9%D0%BE%D0%BD_%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D1%8B)
    #Информация о населении, плотности населения, площади тестового района 2 https://ru.wikipedia.org/wiki/%D0%9E%D1%82%D1%80%D0%B0%D0%B4%D0%BD%D0%BE%D0%B5_(%D1%80%D0%B0%D0%B9%D0%BE%D0%BD_%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D1%8B)

    def __init__(self, name,  power, powerStations, population, density, MKD, malls, gasStations, parkings):

        self.name = name
       # self.type = type
        self.power = power * 0.71 * 1000 #кВт, переведено из МВА
        self.powerStations = powerStations
        self.population = population
        self.density = density
        self.MKD = MKD
        self.malls = malls
        self.gasStations = gasStations
        self.parkings = parkings
        self.evcars = 118000 * population / 12655050
        self.area = population / density


class OutputData:

    def __init__(self, lpChargers, mpChargers, hpChargers, powerUsage, positioning = {'malls' : 0, 'gasStations' : 0, 'parkings' : 0, 'MKD': 0}, costs = {'hpMin' : 0, 'hpMax' : 0, 'mpMin' : 0, 'mpMax' : 0, 'lpMax' : 0}):

        self.lpChargers = lpChargers
        self.mpChargers = mpChargers
        self.hpChargers = hpChargers
        self.powerUsage = powerUsage
        self.positioning = positioning
        self.costs = costs

#Версия расчета с ограничением по ожидаемому кол-ву зарядок
#update: учет использования резерва района по мощности
#update: оценка опреациооных расходов для предложенного решения внутри района
def resolve3(inputData: InputData, powerUsage, MKDperParking):
    #Пре-инициализация
    outputData = OutputData(lpChargers=0, mpChargers=0, hpChargers=0, powerUsage=0, positioning={'malls': 0, 'gasStations': 0, 'parkings': 0, 'MKD': 0}, costs = {'hpMin' : 0, 'hpMax' : 0, 'mpMin' : 0, 'mpMax' : 0, 'lpMax' : 0})

    #Номинальные мощности разных зарядных станций, кВт
    lp = 3.5
    mp = 50
    hp = 150

    #Стоимость обслуживания станций зарядки, операционные раходы, руб
    hpCostsMin = 150000
    hpCostsMax = 300000
    mpCostsMin = 80000
    mpCostsMax = 120000
    lpCostsMax = 50000

    #Ожидаемое количество зарядных станций, рассчитанное из предположения 1 станция на 10 электроавтомобилей
    expectedStations = round(0.1 * inputData.evcars)

    lpExpected = round(0.6 * expectedStations)
    mpExpected = round(0.2 * expectedStations)
    hpExpected = round(0.2 * expectedStations)

    if hpExpected > inputData.gasStations:
        outputData.hpChargers += inputData.gasStations
        outputData.positioning['gasStations'] += inputData.gasStations
        lpExpected += hpExpected - inputData.gasStations
    else:
        outputData.hpChargers += hpExpected
        outputData.positioning['gasStations'] += hpExpected

    if mpExpected > inputData.malls:
        outputData.mpChargers += inputData.malls
        outputData.positioning['malls'] += inputData.malls
        lpExpected += mpExpected - inputData.malls
    else:
        outputData.mpChargers += mpExpected
        outputData.positioning['malls'] += mpExpected

    outputData.lpChargers += lpExpected
    if inputData.MKD/MKDperParking < lpExpected:
        outputData.positioning['MKD'] += round(inputData.MKD/MKDperParking)
        outputData.positioning['parkings'] += round(lpExpected - inputData.MKD/MKDperParking)
    else:
        outputData.positioning['MKD'] += lpExpected

    outputData.powerUsage = (outputData.lpChargers * lp + outputData.mpChargers * mp + outputData.hpChargers * hp) / inputData.power

    if outputData.powerUsage > powerUsage:
        if outputData.positioning['parkings'] > 0:
            while ((outputData.lpChargers * lp + outputData.mpChargers * mp + outputData.hpChargers * hp) / inputData.power > powerUsage) and (outputData.positioning['parkings'] > 0):
                outputData.positioning['parkings'] -= 1
                outputData.lpChargers -=1

    outputData.powerUsage = (outputData.lpChargers * lp + outputData.mpChargers * mp + outputData.hpChargers * hp) / inputData.power

    if outputData.powerUsage > powerUsage:
        if outputData.positioning['MKD'] > 0:
            while ((outputData.lpChargers * lp + outputData.mpChargers * mp + outputData.hpChargers * hp) / inputData.power > powerUsage) and (outputData.positioning['MKD'] > 0):
                outputData.positioning['MKD'] -= 1
                outputData.lpChargers -=1

    sumStations = outputData.lpChargers + outputData.mpChargers + outputData.hpChargers
    outputData.powerUsage = (outputData.lpChargers * lp + outputData.mpChargers * mp + outputData.hpChargers * hp) / inputData.power

    outputData.costs['hpMin'] = outputData.hpChargers * hpCostsMin
    outputData.costs['hpMax'] = outputData.hpChargers * hpCostsMax
    outputData.costs['mpMin'] = outputData.mpChargers * mpCostsMin
    outputData.costs['mpMax'] = outputData.mpChargers * mpCostsMax
    outputData.costs['lpMax'] = outputData.lpChargers * lpCostsMax

    print('Total amount os stations is ' + str(sumStations))
    print('There are ' + str(round(expectedStations)) + ' stations to expect in 2030')
    print('Setted usage of the backup energy power is ' + str(round(powerUsage*1000)/10) + '%')
    if expectedStations < sumStations: print('There are ' + str(round(expectedStations)) + ' stations to expect in 2030, so the amount of suggested stations can be decreased.')
    print('There are suggestion to use:')
    print('3.5 kW chargers: ' + str(outputData.lpChargers))
    print('50 kW chargers:  ' + str(outputData.mpChargers))
    print('150 kW chargers: ' + str(outputData.hpChargers))

    if outputData.positioning['parkings'] > 0:      print('At existing parkings:    ' + str(outputData.positioning['parkings']) + ' of 3.5 kW')
    if outputData.positioning['malls'] > 0:         print('At existing malls:       ' + str(outputData.positioning['malls']) + ' of 50 kW')
    if outputData.positioning['gasStations'] > 0:   print('At existing gasStations: ' + str(outputData.positioning['gasStations']) + ' of 150 kW')
    if outputData.positioning['MKD'] > 0:   print('At existing MKDs:        ' + str(outputData.positioning['MKD']) + ' of 3.5 kW')
    print('Power usage of the backup energy power is ' + str(round(outputData.powerUsage*1000)/10) + '%')
    print('----------------Economics----------------')
    print('OPEX for 150 kW charges: ' + str(outputData.costs['hpMin']) + '...' + str(outputData.costs['hpMax']))
    print('OPEX for 50 kW charges:  ' + str(outputData.costs['mpMin']) + '...' + str(outputData.costs['mpMax']))
    print('OPEX for 3,5 kW charges:  up to ' + str(outputData.costs['lpMax']))
    return outputData

testData = InputData('Lefortovo', power = 38.47, powerStations=18, population= 95070, density=10493, MKD=269, malls=3, gasStations=9, parkings=65)
testData2 = InputData('Otradnoye', power = 21.58, powerStations=35, population= 185459, density=18253, MKD=157, malls=4, gasStations=12, parkings=92)


testOutput3 = resolve3(testData, 0.15, 2)