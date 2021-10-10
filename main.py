# Класс входных данных для района Москвы
class InputData:

    # Информация о резерве мощности https://utp.rossetimr.ru/map-epc?roistat_visit=228566
    # Информация о количестве парковок, АЗС, ТЦ, МКД https://openstreetmap.ru/?roistat_visit=228566#map=13/55.7577/37.6568
    # Информация о населении, плотности населения, площади тестового района 1 https://ru.wikipedia.org/wiki/%D0%9B%D0%B5%D1%84%D0%BE%D1%80%D1%82%D0%BE%D0%B2%D0%BE_(%D1%80%D0%B0%D0%B9%D0%BE%D0%BD_%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D1%8B)
    # Информация о населении, плотности населения, площади тестового района 2 https://ru.wikipedia.org/wiki/%D0%9E%D1%82%D1%80%D0%B0%D0%B4%D0%BD%D0%BE%D0%B5_(%D1%80%D0%B0%D0%B9%D0%BE%D0%BD_%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D1%8B)

    def __init__(self, name,  power, powerStations, population, density, MKD, malls, gasStations, parkings):

        self.name = name                                    # название района
        self.power = power * 0.71 * 1000                    # кВт, переведено из МВА, резерв района
        self.powerStations = powerStations                  # количесто подстанций
        self.population = population                        # население (общая численность)
        self.density = density                              # плотность населения
        self.MKD = MKD                                      # количество многоквартирных домов в районе
        self.malls = malls                                  # количество ТЦ
        self.gasStations = gasStations                      # количество АЗС
        self.parkings = parkings                            # количество парковок разного назначения
        self.evcars = 118000 * population / 12655050        # ожидаемое количество электромобилей в районе к 2030 году

# Класс входных данных для района Москвы
class OutputData:

    def __init__(self, lpChargers, mpChargers, hpChargers, powerUsage, positioning = {'malls' : 0, 'gasStations' : 0, 'parkings' : 0, 'MKD': 0}, costs = {'hpMin' : 0, 'hpMax' : 0, 'mpMin' : 0, 'mpMax' : 0, 'lpMax' : 0}):

        self.lpChargers = lpChargers        # количество 3.5 kW зарядок в районе
        self.mpChargers = mpChargers        # количество 50 kW зарядок в районе
        self.hpChargers = hpChargers        # количество 150 kW зарядок в районе
        self.powerUsage = powerUsage        # нагрузка на резерв района
        self.positioning = positioning      # распределение зарядок по удобным локациям района
        self.costs = costs                  # операционные расходы на содержание полученного решения

# Метод для получения решения (основной алгоритм)
# Версия расчета с ограничением по ожидаемому кол-ву зарядок
# update: учет использования резерва района по мощности
# update: оценка опреациооных расходов для предложенного решения внутри района

def resolve(inputData: InputData, powerUsage, MKDperParking):

    # powerUsage - доля от резерва района, которую мы позволяем использовать в худшем сценарии при одновременной работе всех зардок
    # MKDperParking - количество многоквартирных домов на одну общую парковку

    # Пре-инициализация (skip)
    outputData = OutputData(lpChargers=0, mpChargers=0, hpChargers=0, powerUsage=0, positioning={'malls': 0, 'gasStations': 0, 'parkings': 0, 'MKD': 0}, costs = {'hpMin' : 0, 'hpMax' : 0, 'mpMin' : 0, 'mpMax' : 0, 'lpMax' : 0})

    # Номинальные мощности разных зарядных станций, кВт
    lp = 3.5
    mp = 50
    hp = 150

    # Стоимость обслуживания станций зарядки, операционные раходы, руб
    hpCostsMin = 150000
    hpCostsMax = 300000
    mpCostsMin = 80000
    mpCostsMax = 120000
    lpCostsMax = 50000

    # Ожидаемое количество зарядных станций, рассчитанное из предположения 1 станция на 10 электроавтомобилей
    expectedStations = round(0.1 * inputData.evcars)

    # Первое приближение по распределению мощностей среди зарядных станций в соответствии с http://government.ru/docs/43060/
    lpExpected = round(0.6 * expectedStations)
    mpExpected = round(0.2 * expectedStations)
    hpExpected = round(0.2 * expectedStations)

    # Распределение зарядных станций высокой и средней мощности в локации района с агрессивными сценариями использования
    # Раскидка быстрых зарядок по локациям с АЗС, доступных из первого приближения:
    # Остаток (неиспользованные зарядки) возвращается в квоту маломощных зарядок
    if hpExpected > inputData.gasStations:
        outputData.hpChargers += inputData.gasStations
        outputData.positioning['gasStations'] += inputData.gasStations
        lpExpected += hpExpected - inputData.gasStations
    else:
        outputData.hpChargers += hpExpected
        outputData.positioning['gasStations'] += hpExpected

    # Раскидка средних по скорости зарядок по локациям с ТЦ, доступных из первого приближения:
    # Остаток (неиспользованные зарядки) возвращается в квоту маломощных зарядок
    if mpExpected > inputData.malls:
        outputData.mpChargers += inputData.malls
        outputData.positioning['malls'] += inputData.malls
        lpExpected += mpExpected - inputData.malls
    else:
        outputData.mpChargers += mpExpected
        outputData.positioning['malls'] += mpExpected

    # Раскидка маломощных зарядок по локациям дворовых парковок:
    # Остаток (неиспользованные зарядки) перекидывается на остальные типы парковок
    outputData.lpChargers += lpExpected
    if inputData.MKD/MKDperParking < lpExpected:
        outputData.positioning['MKD'] += round(inputData.MKD/MKDperParking)
        outputData.positioning['parkings'] += round(lpExpected - inputData.MKD/MKDperParking)
    else:
        outputData.positioning['MKD'] += lpExpected

    # Оценка использования резерва района для технологического подключения
    outputData.powerUsage = (outputData.lpChargers * lp + outputData.mpChargers * mp + outputData.hpChargers * hp) / inputData.power

    # Избавление от зарядок, превышающих установленное использование резерва по мощности района
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

    # Статистика
    sumStations = outputData.lpChargers + outputData.mpChargers + outputData.hpChargers
    outputData.powerUsage = (outputData.lpChargers * lp + outputData.mpChargers * mp + outputData.hpChargers * hp) / inputData.power

    # Оценка операционных расходов на предложенное распределение по мощностям среди ожидаемого количества установленных зарядок
    outputData.costs['hpMin'] = outputData.hpChargers * hpCostsMin
    outputData.costs['hpMax'] = outputData.hpChargers * hpCostsMax
    outputData.costs['mpMin'] = outputData.mpChargers * mpCostsMin
    outputData.costs['mpMax'] = outputData.mpChargers * mpCostsMax
    outputData.costs['lpMax'] = outputData.lpChargers * lpCostsMax

    # Форматированный выход (skip)
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



# Создание входных данных по открытым источникам

testData = InputData('Lefortovo', power = 38.47, powerStations=18, population= 95070, density=10493, MKD=269, malls=3, gasStations=9, parkings=65)
testData2 = InputData('Otradnoye', power = 21.58, powerStations=35, population= 185459, density=18253, MKD=157, malls=4, gasStations=12, parkings=92)

# Тест алгоритма
print('1111111111111111111111111111111111111111111111')
testOutput = resolve(testData, 0.15, 2)
print('2222222222222222222222222222222222222222222222')
testOutput2 = resolve(testData2, 0.15, 2)