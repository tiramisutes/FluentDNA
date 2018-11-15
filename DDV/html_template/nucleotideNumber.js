var PRECISION = 10;      // number of decimal places
var viewer = null;
var pointerStatus = "";
var cursor_in_a_title = false;
var ColumnNumber = 0;
var ColumnRemainder = "";
var PositionInColumn = "";
var iNucleotidesPerColumn = columnWidthInNucleotides * originalImageHeight;
var ColumnWidth = ColumnPadding + columnWidthInNucleotides;
var originalAspectRatio = originalImageHeight / originalImageWidth;
var Nucleotide = "";
var NucleotideY = "-";
var nucNumX = 0;
var nucNumY = 0;

var contigs = {};
var visible_seq_obj;
var theSequenceSplit = []; // used globally by density service
var theSequence = "";
var fragmentid = "";
var sequence_data_loaded = 0;
var sequence_data_viewer_initialized = 0;

function init_all(){
    /** Iterates through each chromosome container and initializes and OpenSeaDragon
     * view using the source directory specified in 'data-chr-source' */
    $(".chromosome-container").each(function(index, element){
        init($(element).attr("id"), $(element).attr("data-chr-source"));
    });
}

function init(container_id, source_folder) {
    var source = source_folder == "" ? "" : source_folder + "/"; //ensure directories end with a slash
    source += "GeneratedImages/dzc_output.xml";
    viewer = OpenSeadragon({
        id: container_id,
        prefixUrl: "img/",
        showNavigator: true,
        tileSources: [source],
        maxZoomPixelRatio: 20
    });
    viewer.scalebar({
        type: OpenSeadragon.ScalebarType.MAP,
        pixelsPerMeter: 1,
        minWidth: "70px",
        location: OpenSeadragon.ScalebarLocation.BOTTOM_LEFT,
        xOffset: 5,
        yOffset: 10,
        stayInsideImage: false,
        color: "rgb(30, 30, 30)",
        fontColor: "rgb(10, 10, 10)",
        backgroundColor: "rgba(255, 255, 255, 0.5)",
        fontSize: "normal",
        barThickness: 1,
        sizeAndTextRenderer: OpenSeadragon.ScalebarSizeAndTextRenderer.BASEPAIR_LENGTH
    });

    OpenSeadragon.addEvent(viewer.element, "mousemove", function(event){showNucleotideNumber(event, viewer);});

    //copy content of pointed at sequence fragment to result log
    $("body").keyup(function (event) {
        if (theSequence) {
            if (event.keyCode == 88) {
                $("#outfile").prepend("<div class='sequenceFragment'><div style='background-color:#f0f0f0;'>" + fragmentid + "</div>" + theSequence + "</div>");
            }
        }
    });

    $("#SequenceFragmentInstruction").hide();
    $("#getSequenceButton").hide();
}

function numberWithCommas(x) {
    return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function classic_layout_mouse_position(nucNumX, nucNumY) {
    var Nucleotide = "";

    ColumnNumber = Math.floor(nucNumX / ColumnWidth);
    ColumnRemainder = nucNumX % ColumnWidth;

    PositionInColumn = ColumnRemainder + 1;
    NucleotideY = columnWidthInNucleotides * nucNumY;

    if ((ColumnRemainder <= ColumnWidth) && (ColumnRemainder >= columnWidthInNucleotides )) {
        ColumnNumber = "";
        PositionInColumn = "";
        pointerStatus = "Outside of Image (Inbetween Columns)";
    }
    else {
        Nucleotide = iNucleotidesPerColumn * ColumnNumber + NucleotideY + PositionInColumn;
        if (Nucleotide > ipTotal) {
            //End of Sequence
            Nucleotide = "";
        }

    }
    return Nucleotide;
}

function nucleotide_coordinates_to_sequence_index(index_from_xy){
    cursor_in_a_title = false;
    var contig_name = "";
    var index_inside_contig = 0;
    var file_coordinates = "";
    for (var i = 0; i < ContigSpacingJSON.length; i++) {
        var contig = ContigSpacingJSON[i];
        if (contig.xy_seq_end > index_from_xy) { // we're in range of the right contig
            if (contig.xy_title_start > index_from_xy) { //we overshot and haven't reached title
                break;
            }
            if (contig.xy_seq_start <= index_from_xy) {// cursor is in nucleotide body
                index_inside_contig = index_from_xy - contig.xy_seq_start + 1;
                file_coordinates = contig.nuc_seq_start + index_inside_contig;
                contig_name = contig.name;
                break;
            } else {// cursor is in label
                cursor_in_a_title = true;
                contig_name = contig.name;
                break;
            }
        }
    }
    return {contig_name: contig_name,
        index_inside_contig: index_inside_contig,
        file_coordinates: file_coordinates};
}


function tiled_layout_mouse_position(nucNumX, nucNumY) {
    //global variable layout_levels set by Form1.cs
    var index_from_xy = 0;
    var xy_remaining = [nucNumX, nucNumY];
    for (var i = layout_levels.length - 1; i >= 0; i--) {
        var level = layout_levels[i];
        var part = i % 2;
        var number_of_full_increments = Math.floor(xy_remaining[part] / level.thickness);
        // add total nucleotide size for every full increment of this level e.g. Tile Y height
        index_from_xy += level.chunk_size * number_of_full_increments;
        //subtract the credited coordinates to shift to relative coordinates in that level
        xy_remaining[part] -= number_of_full_increments * level.thickness;

        if (xy_remaining[part] >= level.thickness - level.padding && xy_remaining[part] < level.thickness) {
            return "";//check for invalid coordinate (margins)
        }
    }
    var position_info = nucleotide_coordinates_to_sequence_index(index_from_xy);
    return position_info;
}

function showNucleotideNumber(event, viewer) {
    /** getMousePosition() returns position relative to page,
     * while we want the position relative to the viewer
     * element. so subtract the difference.*/
    var pixel = OpenSeadragon.getMousePosition(event).minus(OpenSeadragon.getElementPosition(viewer.element));
    if (!viewer.isOpen()) {
        return;
    }
    var point = viewer.viewport.pointFromPixel(pixel);
    var position_info = {};
    var information_to_show = false;
    cursor_in_a_title = false;

    if ((point.x < 0) || (point.x > 1)) {
        nucNumX = "-";
        Nucleotide = "";
        pointerStatus = "Outside of Image (X)";
    }
    else {
        nucNumX = Math.round(point.x * originalImageWidth - 0.5) - image_origin[0];
    }

    if ((point.y < 0) || (point.y > originalAspectRatio)) {
        nucNumY = "-";
        Nucleotide = "";
        pointerStatus = "Outside of Image (Y)";
    }
    else {
        nucNumY = Math.round(point.y * originalImageWidth - 0.5) - image_origin[1];
    }

    if ((nucNumX != "-") && (nucNumY != "-")) {
        position_info = tiled_layout_mouse_position(nucNumX, nucNumY);
        information_to_show = $.isNumeric(position_info.file_coordinates)
    }

    var display = information_to_show ? position_info.index_inside_contig : "-";
    if(cursor_in_a_title){
        display = position_info.contig_name;
    }
    document.getElementById("Nucleotide").innerHTML = numberWithCommas(display);

    //show sequence fragment
    if (sequence_data_viewer_initialized) {
        var lineNumber = "";
        if (information_to_show && position_info.index_inside_contig) {
            Nucleotide = position_info.index_inside_contig;
            lineNumber = Math.floor(Nucleotide / columnWidthInNucleotides);
            var remainder = Nucleotide % columnWidthInNucleotides + columnWidthInNucleotides;
            var start = Math.max(0, (lineNumber - 1) * columnWidthInNucleotides); // not before begin of seq
            var stop = Math.min(ipTotal, (lineNumber + 2) * columnWidthInNucleotides); //+2 = +1 start then + width of column
            if(lineNumber == 0){ // first line of the contig
                remainder -= columnWidthInNucleotides;
            }
            if(cursor_in_a_title){
                start = Nucleotide - 1;
                stop = Nucleotide;
            }
            theSequence = contigs[position_info.contig_name].substring(start, stop);
            //theSequence = theSequence.replace(/\s+/g, '')
            //user visible indices start at 1, not 0
            fragmentid = position_info.contig_name + ": (" +
              numberWithCommas(start + 1) + " - " + numberWithCommas(stop) + ")";
            visible_seq_obj.setSequence(theSequence, fragmentid);
            visible_seq_obj.setSelection(remainder, remainder);

            $('#SequenceFragmentInstruction').show();

        }
        else {
            visible_seq_obj.clearSequence("");
            theSequence = "";
            fragmentid = "";
            $('#SequenceFragmentInstruction').hide();
        }
    }

}

function addLoadEvent(func) {
    var oldOnLoad = window.onload;
    if (typeof window.onload != 'function') {
        window.onload = func;
    }
    else {
        window.onload = function () {
            if (oldOnLoad) {
                oldOnLoad();
            }
            func();
        }
    }
}

function getSequence() {


    $.ajax({xhr: function()
    {
        var xhr = new window.XMLHttpRequest();
        //Download progress
        xhr.addEventListener("load", function (evt) {
            $("#status").html("Sequence data loaded.  Display of sequence fragments activated.");
            // $("#btnCallGCSkew").click(function (event) {
            //     GenerateGCSkewChart();
            // });
            // $("#status").append("<div id='gc-skew-plot-button'>Generate GC Skew activated.");
            sequence_data_loaded = 1;
        }, false);
        xhr.addEventListener("progress", function (evt) {
            if (evt.lengthComputable) {
                var percentComplete = (evt.loaded / evt.total) * 100;
                //Do something with download progress
                if (percentComplete < 100) {
                    $("#status").html("<img src='img/loading.gif' /> Loading sequence data: " + parseFloat(percentComplete).toFixed(2) + "% complete");
                }
            }
            else {
                $("#status").html("<img src='img/loading.gif' />Loading sequence data  ... [ " + parseFloat(evt.loaded / 1048576).toFixed(2) + " MB loaded ]");
            }
        }, false);
        return xhr;
    },
        type: "GET",
        url: fasta_source[0],
        contentType: "text/html",
        success: initSequence,
        error: processInitSequenceError
    });
}

function read_contigs(sequence_received) {
    //read_contigs equiv in javascript
    theSequenceSplit = sequence_received.split(/^>|\n>/);// begin line, caret  ">");
    var contigs = {}
    for (let contig_s of theSequenceSplit) {
        var lines = contig_s.split(/\r?\n/);
        var title = lines[0]
        var seq = lines.slice(1).join('');
        contigs[title] = seq;
    }
    return contigs
}
function initSequence (sequence_received) {
    contigs = read_contigs(sequence_received);

    visible_seq_obj = new Biojs.Sequence({
        sequence : "",
        target : "SeqDisplayTarget",
        format : 'FASTA',
        columns : {size:columnWidthInNucleotides,spacedEach:0} ,
        formatSelectorVisible: false,
        fontSize: '18px',
    });
    sequence_data_viewer_initialized=1;
    visible_seq_obj.clearSequence("");
    $('#SequenceFragmentInstruction').hide();
}

function processInitSequenceError() {
    //do nothing
};

addLoadEvent(init_all);
addLoadEvent(getSequence);


function outputTable() {
    document.write('<table id="output" style="border: 1px solid #000000;"><tr><th>Nucleotide Number</th><td id="Nucleotide">-</td></tr></table>    ' +
      '<div id="getSequenceButton"><br /><a onclick="getSequence()"> Fetch Sequence </a></div>' +
      '<div id="base"></div><div id="SequenceFragmentFASTA" style="height:200px;">' +
        '<div id="SeqDisplayTarget"></div>' +
        '<div id="SequenceFragmentInstruction" style="display: block;margin-top: -25px;">' +
          'Press "x" key using keyboard to copy this fragment to Result Log</div>' +
        '<div id="status_box">' +
          '<span style="font-weight: bolder;color: darkgrey;font-family: sans-serif;">Status: </span>' +
          '<div id="status"></div>' +
      '</div>' +
      '</div>' +
      '<table class="output" style="border: 1px solid #000000;visibility:hidden;display:none;">' +
        '<tr><th class="name">' +
        '</th><th class="value">Pixels</th><th class="value">Points</th></tr>' +
        '<tr><th>Mouse position</th><td id="mousePixels">-</td><td id="mousePoints">-</td></tr>' +
        '<tr><th>X, Y</th><td id="nucleotideNumberX">-</td><td id="nucleotideNumberY">-</td><td></td></tr>' +
        '<tr><th>(X, Y)</th><td id="NucleotideNumberX">-</td><td id="NucleotideNumberY">-</td></tr>' +
        '<tr><th>Column Number</th><td id="ColumnNumber">-</td><td id="ColumnRemainder">-</td></tr>' +
        '<tr><th>Nucleotide Number</th><td id="Nucleotide">-</td><td>-</td></tr>' +
        '<tr><th>Nucleotides in Local Column</th>   <td id="NucleotideY">-</td><td>-</td></tr>' +
        '<tr><th>Position in Column</th><td id="PositionInColumn">-</td><td></td></tr>' +
        '<tr><th>Nucleotides Per Column</th><td id="iNucleotidesPerColumn">-</td><td></td></tr>' +
        '<tr><th>Aspect Ratio</th><td id="aspectRatio">-</td><td></td></tr>' +
        '<tr><th>Viewport dimensions</th>' +
        '<td id="viewportSizePixels">-</td><td id="viewportSizePoints">-</td></tr>' +
      '</table>');
}



function uiLoading (message) {
    //var bufferOutFile=$("#outfile").val();
    $("#status").html(" <img src='img/loading.gif' style='float:left;' /><div style='font-size:11pt;padding-top:10px;padding-bottom:15px;'>"+message+"</div>" );
}

function processError() {
    $("#outfile").prepend("<br />Error.  Connection problem. <div class='resultdivider'></div>");
    $("#status").html("Completed with error." );
}