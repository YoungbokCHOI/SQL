##// This source code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
##// © Kioseff Trading

##//@version=5
indicator("The Next Pivot [Kioseff Trading]", overlay=true, max_lines_count = 500, max_boxes_count = 500, max_labels_count = 500)


import TradingView/ZigZag/6 as ZigZagLib 
import HeWhoMustNotBeNamed/arraymethods/1
import RicardoSantos/MathOperator/2

historical    = input.int(defval = 20, title = "Correlation Length", minval = 5, maxval = 100, group = "How Long Should The Correlating Sequences Be? (Bars Back)")
forecastLen   = input.int(defval = 50, minval = 15, maxval = 250, title = "Forecast Length", group = "How Long Should The Forecast Be?")

typec         = input.string("Cosine Similarity", title = "Similarity Calculation", options = 
 ["Spearmen", "Pearson", "Euclidean (Absolute Difference)", "Cosine Similarity", "Mean Squared Error", "Kendall"], group = "Similarity Method"), var t = time
simtype       = input.string(defval = "Price", title = "Looks For Similarities In", options = ["%Change", "Price"], group = "Similarity Method")
tim           = input.int(defval = 5000, minval = 500, step = 1000, title = "Bars Back To Search", 
             group ="How Many Bars Back Should We Look To Find The Most Similar Sequence?")

zonly         = input.bool(defval = true , title = "Show Projected Zig Zag"   , group = "Aesthetics", inline = "Projected")
ponly         = input.bool(defval = true, title = "Show Projected Price Path",  group = "Aesthetics", inline = "Projected")
on            = input.bool(defval = false, title = "", inline = "Lin", group = "Aesthetics")
stdev         = input.float(defval = 1, title = "Lin Reg σ", minval = 0, step = 0.1, inline = "Lin",  group = "Aesthetics")

projcol       = input.color(defval = #14D990,      title = "Projected Zig Zag Color", inline = "1", group = "Aesthetics")
forecastCol   = input.color(defval = color.white , title = "Forecast Color  ",        inline = "1", group = "Aesthetics")

var ret = array.new_float(), var mastertime = array.new_int(), result = matrix.new<float>(2, 1, -1e8), float [] recRet = na

method rankEstimate(array <float> id, iteration) => 

    math.round((id.percentrank(iteration) / 100) * (historical - 1) + 1)

method effSlice(array<float> id, iteration) => 

    id.slice(iteration, iteration + historical)

method update (matrix <float> id, float id2, i) => 

    if id2.over_equal(id.get(0, 0))

        id.set(0, 0, id2)
        id.set(1, 0, i)

method spearmen (matrix <float> id) =>


    denominator = (historical * (math.pow(historical, 2) - 1))
    estimate    = array.new_int()

    for i = 0 to recRet.size() - 1
        estimate.push(recRet.rankEstimate(i))

    for i = 0 to ret.size() - historical * 2 - forecastLen
            
        slice = ret.effSlice(i)
        d2    = array.new_float(historical)

        for x = 0 to historical - 1

            s   = estimate.get(x)
            s1  = slice.rankEstimate(x)
            fin = math.pow(s - s1, 2)
            d2.set(x, fin)
        
        r  = 1 - (6 * d2.sum()) / denominator

        id.update(i, r)

method pearson (matrix <float> id) => 
        
    stdevA = recRet.stdev() 

    for i = 0 to ret.size() - historical * 2 - forecastLen

        slice = ret.effSlice(i)
        p     = slice.covariance(recRet) / (stdevA * slice.stdev())

        id.update(p, i)

method euc (matrix <float> id) => 

    for i = 0 to ret.size() - historical * 2 - forecastLen
                
        slice = ret.effSlice(i)
        euc   = array.new_float(historical)
             
        for x = 0 to historical - 1

            euc.set(x, math.pow(recRet.get(x) - slice.get(x), 2))

        inv = 1 / (1 + math.sqrt(euc.sum()))

        id.update(inv, i)


method cosine(matrix <float> id) => 
    
    nA = 0.

    for i = 0 to recRet.size() - 1
        nA += math.pow(recRet.get(i), 2)

    nA := math.sqrt(nA)

    for i = 0 to ret.size() - historical * 2 - forecastLen
            
        slice = ret.effSlice(i)
        prod  = 0., nB = 0.

        for x = 0 to historical - 1

            prod += recRet.get(x) * slice.get(x)
            nB   += math.pow(slice.get(x), 2)
        
        cos = prod / (nA * math.sqrt(nB))
        id.update(cos, i)

    
method mse (matrix <float> id) => 
    
    for i = 0 to ret.size() - historical * 2 - forecastLen
            
        slice = ret.effSlice(i)
        mse   = array.new_float(historical)

        for x = 0 to historical - 1
            mse.set(x, math.pow(slice.get(x) - recRet.get(x), 2))

        mseC = 1 / (1 + mse.sum() / historical)

        id.update(mseC, i)


method kendall (matrix <float> id) => 

    for i = 0 to ret.size() - historical * 2 - forecastLen
         
        slice     = ret.effSlice(i)
        valMat    = matrix.new<float>(4, math.ceil(slice.size() * (slice.size() - 1) / 2), 0)
        iteration = 0

        for x = 0 to slice.size() - 1
            for y = x + 1 to historical - 1
                if y > historical - 1
                    break

                diff1 = recRet.get(y)   - recRet.get(x)
                diff2 = slice.get(y) - slice.get(x)

                switch math.sign(diff1 * diff2)

                    1  => valMat.set(0, iteration, 1)
                    -1 => valMat.set(1, iteration, 1)

                if diff1.equal(0)
                    valMat.set(2, iteration, 1)

                if diff2.equal(0)
                    valMat.set(3, iteration, 1)
                
                iteration += 1    

        con = valMat.row(0).sum(), dis = valMat.row(1).sum()
        aT  = valMat.row(2).sum(), bT  = valMat.row(3).sum()

        fin = (con - dis) / math.sqrt((con + dis + aT) * (con + dis + bT))

        id.update(fin, i)

method determine(bool id, a, b) => 

    switch id 
        
        true => a
        =>      b

method updateZig(array <line> id, x1, y1, x2, y2) => 

    id.push(line.new(x1, y1, x2, y2, color = projcol, width = 2))

method float (int id) => float(id) 


var zigZag = ZigZagLib.newInstance(
  ZigZagLib.Settings.new(
      0.00001,     //input.float(0.00001, "Price deviation for reversals (%)", 0.00001, 100.0, 0.5, "0.00001 - 100", group = "Aesthetics"),
      5,           //input.int(5, "Pivot legs", 2, group = "Aesthetics"),
      #00000000, //input(#2962FF, "Line color", group = "Aesthetics", inline = "1"),
      false,       //input(true, "Extend to last bar"),
      false,       //input(false, "Display reversal price", group = "Aesthetics"),
      false,       //input(false, "Display cumulative volume", group = "Aesthetics"),
      false,       //input(false, "Display reversal price change", inline = "priceRev", group = "Aesthetics"),
      "Absolute",  //input.string("Absolute", "", ["Absolute", "Percent"], inline = "priceRev", group = "Aesthetics"),
      true)
 ),                                     zigZag.update()

if typec == "Kendall"

    tim        := math.min(tim, 1500)
    historical := math.min(20, historical)


var closeArr = array.new_float(), var loArr    = array.new_float()
var hiArr    = array.new_float(), var timeArr  = array.new_int  (),
                         mastertime.push(time)

if last_bar_index - bar_index <= tim
    
    val = switch simtype

        "%Change" => math.log(close / close[1])
        =>           close

    timeArr .push(time), closeArr.push(close)
    ret     .push(val) , loArr   .push(low),
             hiArr   .push(high)

if barstate.islastconfirmedhistory 

    lineAll = line.all, box.all.flush()
    var xcor = last_bar_index 

    for i = 0 to lineAll.size() - 1
        if lineAll.get(i).get_x2() > t

            for x = mastertime.size() - 1 to 0 
                if mastertime.get(x).float().equal(lineAll.get(i).get_x2())

                    xcor := x
                    break   
    
    if lineAll.size().float().over(0) 
        for i = lineAll.size() - 1 to 0
            if lineAll.get(i).get_x2().float().under(1e8)
                lineAll.get(i).delete()

    recRet := ret.slice(ret.size() - historical, ret.size())

    switch typec

        "Spearmen"                        => result.spearmen()
        "Pearson"                         => result.pearson ()
        "Euclidean (Absolute Difference)" => result.euc     ()
        "Cosine Similarity"               => result.cosine  ()
        "Mean Squared Error"              => result.mse     ()
        "Kendall"                         => result.kendall ()

    startarr                              = int(result.get(1, 0))
    midarr                                = startarr + historical
    endarr                                = midarr   + forecastLen

    float [] lineData = na
    
    if simtype == "%Change"
        lineData := ret.slice(startarr + historical + 1, endarr + 1)
    
    else 
        lineData := array.new_float()

        for i = startarr + historical + 1 to endarr
            lineData.push(closeArr.get(i) / closeArr.get(i - 1) - 1)
            
    projectZig = array.new_line(), lines = array.new_line(), diffArr = array.new_float()

    if lineAll.size().float().over(0) 
        for i = 1 to lineAll.size() - 1

            diffArr.push(math.abs((lineAll.get(i).get_y2() - lineAll.get(i - 1).get_y2()) / lineAll.get(i - 1).get_y2()))
    
    lasty2 = lineAll.last().get_y2(), lasty22 = lineAll.get(lineAll.size() - 2).get_y2(), 
                         threshold = diffArr.percentile_nearest_rank(25)

    lines.push(line.new(bar_index, close, bar_index + 1, close * (1 + lineData.first()), 
                         color = ponly.determine(forecastCol, #00000000), 
                         style =          line.style_dotted
                         ))

    if zonly 

        projectZig.updateZig(xcor, lineAll.last().get_y2(), bar_index, lasty22.under(lasty2).determine(low, high)) 

    for i = 1 to lineData.size() - 1

        lines.push(
                 
                 line.new(
                     
                     lines.get(i - 1).get_x2(), lines.get(i - 1).get_y2(), lines.get(i - 1).get_x2() + 1, 
                     lines.get(i - 1).get_y2() * (1 + lineData.get(i)), color = ponly.determine(forecastCol, #00000000), style = line.style_dotted))

        if zonly 

            if projectZig.size().float().equal(1)
                
                if lasty22.under(lasty2)

                    var min = 1e8, var max = 0.

                    min := math.min(lines.last().get_y2(), min, projectZig.last().get_y2())

                    switch min.equal(lines.last().get_y2())

                        true => max := 0
                        =>      max := math.max(max, lines.last().get_y2())

                    projectZig.last().set_y2(min)
                    projectZig.last().set_x2(min.equal(lines.last().get_y2()).determine(lines.last().get_x2(), projectZig.last().get_x2()))

                    if math.abs((max - min) / min).over_equal(threshold) and max.not_equal(0) 

                        maxmap = map.new<float, int>(), count = hiArr.size() - 1

                        for x = mastertime.size() - 1 to 0 
                            switch mastertime.get(x) > lineAll.last().get_x2()

                                true => maxmap.put(hiArr.get(count), x)
                                =>      break 

                            count -= 1

                        keymaxx = maxmap.keys()

                        if keymaxx.max() > projectZig.last().get_y1()
                            projectZig.last().set_xy1(maxmap.get(keymaxx.max()), keymaxx.max())


                        projectZig.updateZig(projectZig.last().get_x2(), projectZig.last().get_y2(), lines.last().get_x2(), max) 

                else 

                    if i.float().equal(1)

                        min = map.new<float, int>(), count = loArr.size() - 1

                        for x = mastertime.size() - 1 to 0 

                            switch mastertime.get(x).float().over_equal(lineAll.last().get_x2())

                                true => min.put(loArr.get(count), x)
                                =>      break

                            count -= 1

                        keys = min.keys()

                        if keys.min().under(projectZig.last().get_y2())

                            projectZig.last().set_y2(math.min(keys.min(), lines.last().get_y2()))

                            x2 = switch lines.last().get_y2().under(keys.min())

                                true => lines.last().get_x2()
                                =>      min  .get(keys.min())

                            projectZig.last().set_x2(x2), projectZig.last().set_x1(mastertime.indexof(lineAll.get(lineAll.size() - 2).get_x2()))
                            projectZig.last().set_y1(lineAll.get(lineAll.size() - 2).get_y2())

                            projectZig.updateZig(projectZig.last().get_x2(), projectZig.last().get_y2(), lines.last().get_x2(), lines.last().get_y2())

                    var min = 1e8, var max = 0.

                    max := math.max(lines.last().get_y2(), max)

                    switch max.equal(lines.last().get_y2())

                        true => min := 1e8
                        =>      min := math.min(min, lines.last().get_y2())

                    projectZig.last().set_y2(max)
                    projectZig.last().set_x2(max.equal(lines.last().get_y2()).determine(lines.last().get_x2(), projectZig.last().get_x2()))

                    if math.abs((max - min) / min).over_equal(threshold) and min.not_equal(1e8)

                        projectZig.updateZig(projectZig.last().get_x2(), projectZig.last().get_y2(), lines.last().get_x2(), min) 
    

            else if projectZig.size().float().over(1)

                if projectZig.last().get_y2().over_equal(projectZig.get(projectZig.size() - 2).get_y2())
                    var max =0., var min = 1e8
                    max := math.max(max, lines.last().get_y2(), projectZig.last().get_y2())

                    switch max.equal(lines.last().get_y2())

                        true => min := 1e8
                        =>      min := math.min(min, lines.last().get_y2())

                    projectZig.last().set_y2(math.max(max, projectZig.last().get_y2()))
                    projectZig.last().set_x2(max.equal(lines.last().get_y2()).determine(lines.last().get_x2(), projectZig.last().get_x2()))

                    if math.abs((max - min) / min).over_equal(threshold) and min.not_equal(1e8) 

                        if projectZig.size().float().over(2)
                          or projectZig.size().float().equal(2) and projectZig.first().get_y1().equal(lineAll.last().get_y2())

                            projectZig.updateZig(projectZig.last().get_x2(), projectZig.last().get_y2(), lines.last().get_x2(), min)
   

                        else if projectZig.size().float().equal(2)

                            maxx = map.new<float, int>(), count = hiArr.size() - 1

                            for x = mastertime.size() - 1 to 0 
                                switch mastertime.get(x).float().over(lineAll.last().get_x2())

                                    true => maxx.put(hiArr.get(count), x)
                                    =>      break

                                count -= 1

                            keyMax = maxx.keys()

                            if keyMax.max().over(max) 
                                projectZig.last().set_y2(keyMax.max()), projectZig.last().set_x2(maxx.get(keyMax.max()))

                                if projectZig.last().get_x1().float().not_equal(last_bar_index)

                                    switch lineAll.last().get_x1().float().over(lineAll.last().get_x2())

                                        true => projectZig.last().set_xy1(mastertime.indexof(lineAll.last().get_x1()), lineAll.last().get_y1())                                  
                                        =>      projectZig.last().set_xy1(mastertime.indexof(lineAll.last().get_x2()), lineAll.last().get_y2())

                            projectZig.remove(projectZig.size() - 2).delete()
                            projectZig.updateZig(projectZig.last().get_x2(), projectZig.last().get_y2(), lines.last().get_x2(), min)
    
                        max := 0, min := 1e8

                else if projectZig.last().get_y2().under(projectZig.get(projectZig.size() - 2).get_y2())

                    var min = 1e8, var max = 0.
                    min := math.min(lines.last() .get_y2(), min, projectZig.last().get_y2())

                    switch min.equal(lines.last().get_y2())

                        true =>  max := 0
                        =>       max := math.max(max, lines.last().get_y2())

                    projectZig.last().set_y2(min)
                    projectZig.last().set_x2(min.equal(lines.last().get_y2()).determine(lines.last().get_x2(), projectZig.last().get_x2()))

                    if math.abs((max - min) / min).over_equal(threshold) and max.not_equal(0) 

                        if projectZig.size().float().over(1)

                            max := 0, min := 1e8

                            projectZig.updateZig(projectZig.last().get_x2(), projectZig.last().get_y2(), lines.last().get_x2(), lines.last().get_y2())
  

            if i.float().equal(lineData.size() - 1)
                if projectZig.size().float().equal(1) 

                    valMap = map.new<float, int>()

                    for x = lines.size() - 1 to 0
                        switch lines.get(x).get_x2().float().over(projectZig.last().get_x2())

                            true => valMap.put(lines.get(x).get_y2(), x)
                            =>      break

                    keys = valMap.keys(), cond = projectZig.last().get_y2().under(projectZig.last().get_y1())

                    [finx, finy] = switch cond

                        true => [valMap.get(keys.max()), keys.max()]
                        =>      [valMap.get(keys.min()), keys.min()]

                    projectZig.updateZig(projectZig.last().get_x2(), projectZig.last().get_y2(), bar_index + finx + 1, finy) 

    if on 

        linReg = matrix.new<float>(4, forecastLen)

        for i = 0 to forecastLen - 1

            linReg.set(0, i, i + 1), linReg.set(1, i, lines.get(i).get_y2())

        b = linReg.row(0)

        for i = 0 to lineData.size() - 1

            linReg.set(2, i, math.pow(b.get(i) - b.avg(), 2))
            linReg.set(3, i, (b.get(i) - b.avg()) * (linReg.row(1).get(i) - linReg.row(1).avg()))

        bx = linReg.row(3).sum() / linReg.row(2).sum() 
        mx = linReg.row(1).avg() - (bx * b.avg())

        upper = line.new(bar_index, (bx + mx) + linReg.row(1).stdev() * stdev, bar_index + linReg.row(1).size(), 
                                 (bx * linReg.row(1).size() + mx) + linReg.row(1).stdev() * stdev, 
                                 color = #6929F2
                                 )

        lower = line.new(bar_index, (bx + mx) - linReg.row(1).stdev() * stdev, bar_index + linReg.row(1).size(), 
                                 (bx * linReg.row(1).size() + mx) - linReg.row(1).stdev() * stdev, 
                                 color = #6929F2
                                 )

        linefill.new(upper, lower, color.new(#6929F2, 75))

    slicex    = closeArr.slice(startarr, endarr + 1)    
    sliceHi   = hiArr   .slice(closeArr.size() - historical, closeArr.size())
    sliceLo   = loArr   .slice(closeArr.size() - historical, closeArr.size())

    box.new(timeArr.get(startarr), slicex.min(), timeArr.get(midarr), slicex.max(), 
                                     bgcolor      = color.new(color.blue, 70),
                                     xloc         = xloc.bar_time,
                                     border_color = #00000000
                                     )
    
    box.new(timeArr.get(midarr), slicex.min(), timeArr.get(endarr), slicex.max(), 
                                     bgcolor      = color.new(forecastCol, 70),
                                     xloc         = xloc.bar_time, 
                                     border_color = #00000000
                                     )

    box.new(bar_index - historical + 1, sliceHi.max(), bar_index, sliceLo.min(), 
                             bgcolor      = color.new(color.blue, 80), 
                             border_color = #00000000
                             )

    var tab = table.new(position.bottom_right, 5, 5, frame_color = color.white, border_color = color.white, frame_width = 1, border_width = 1)

    tab.cell(0, 0, text = "Searching " + str.tostring(math.min(last_bar_index, tim), "##") + " Bars Back",     
                                         text_color = color.white,
                                         text_size  = size.small   ,
                                         bgcolor    = #00000050)
