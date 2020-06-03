(function(){
var app = angular.module('IDOC');


app.directive('input', function() {

    return {
      restrict: 'E',
      link: link
    };

    function link(scope, elem, attrs) {
        elem.on('focus', function() {
            console.log(elem[0].name + ' has been focused!');
            scope.in_focus = elem[0].name;
        });
    elem.on('blur', function() {
            console.log(elem[0].name + ' has been blurred!');
            scope.in_focus = undefined;
    })
    }
});

app.directive('focusMe', function($timeout, $parse) {
    return {
        link: function(scope, element, attrs) {

            var model = $parse(attrs.focusMe);
            scope.$watch(model, function(value) {
                if(value === true) {
                    $timeout(function() {
                        element[0].focus()
                    });
                }

            });
            //
        }
    }
})


app.controller('deviceController', function($scope, $http, $routeParams, $interval, $timeout, $location)  {

        device_id = $routeParams.device_id;

        $scope.device = {}; //the info about the device
        $scope.server = {}; // to control the device
        $scope.showLog = false;
        $scope.can_stream = false;
        $scope.isActive = false;
        var refresh_data = false;
        var spStart= new Spinner(opts).spin();
        var starting_tracking= document.getElementById('starting');



        $scope.post_wrapper = function(data) {
            /*
            Return a function that when called posts data to the API endpoint
            that updates the user settings.
            */

            f = function() {
                $http.get('/device/' + device_id + '/settings').success(function(data) {
                })
            };

            return f

        };

        $scope.button_wrapper = function(device_id, module, action) {
            /*
            Return a function that when called posts action to a module
            in the right API endpoint
            */

            f = function() {

                $http.get('/device/' + id + '/controls/' + module + '/' + action).success(function(data) {
                    // debugger;
                    console.log($scope.device);
                    $scope.device[module]["status"] = data["status"];
                })
            };

            return f

        };

        $http.get('/device/'+device_id+'/info').success(function(data){
            console.log("DATA");
            console.log(data);
            $scope.device = data;

            $scope.server.callbacks = {}


        $scope.server.moduleActions = {
            "tracker": [
                {"name": "ready", "call": $scope.button_wrapper(device_id, "tracker", "ready")},
                {"name": "run", "call": $scope.button_wrapper(device_id, "tracker", "run")},
                {"name": "stop", "call": $scope.button_wrapper(device_id, "tracker", "stop")}
            ],

            "controller": [
                {"name": "run", "call": $scope.button_wrapper(device_id, "controller", "run")},
                {"name": "stop", "call": $scope.button_wrapper(device_id, "controller", "stop")}
            ]
        };

    })


        // watch the attributes array for changes
        // everytime it changes, run post_attributes
        // to update the attributes on the server
        $scope.$watch(
            // what to watch i.e. $scope.input
            // we dont have to type $scope., just input
            $scope.device.settings,
            // what do to upon changes
            $scope.post_wrapper($scope.device.settings),
            // true means: look at all the elements in the array one-by-one
            // i.e. do a deep comparison
            true
        );


        $scope.server.logs = [];
        $scope.server.update_logs = function() {

            $http.get("/device/" + device_id + "/get_logs").success(function(data){
                $scope.server.logs = data["logs"];
                console.log("LOGS");
                console.log(data["logs"]);

            })
        };

        $scope.server.alert= function(message){alert(message);};

        $scope.server.elapsedtime = function(t){
            // Calculate the number of days left
            var days=Math.floor(t / 86400);
            // After deducting the days calculate the number of hours left
            var hours = Math.floor((t - (days * 86400 ))/3600)
            // After days and hours , how many minutes are left
            var minutes = Math.floor((t - (days * 86400 ) - (hours *3600 ))/60)
            // Finally how many seconds left after removing days, hours and minutes.
            var secs = Math.floor((t - (days * 86400 ) - (hours *3600 ) - (minutes*60)))

            if (days>0){
                var x =  days + " days, " + hours + "h, " + minutes + "min,  " + secs + "s ";
            }else if ( days==0 && hours>0){
                var x =   hours + "h, " + minutes + "min,  " + secs + "s ";
            }else if(days==0 && hours==0 && minutes>0){
                var x =  minutes + "min,  " + secs + "s ";
            }else if(days==0 && hours==0 && minutes==0 && secs > 0){
                var x =  secs + " s ";
            }
            return x;

        };
        $scope.server.readable_url = function(url){
            //start tooltips
            $('[data-toggle="tooltip"]').tooltip()
                readable = url.split("/");
                len = readable.length;
                readable = ".../"+readable[len - 1];
                return readable;
        };
         $scope.server.start_date_time = function(unix_timestamp){
            var date = new Date(unix_timestamp*1000);
            return date.toUTCString();
        };

        var refresh = function(){
	    console.log("Refreshing");
        if (document.visibilityState=="visible"){

            $scope.server.update_logs();
            console.log($scope.server.parameters);

            $http.get('/device/'+device_id+'/info')
             .success(function(data){
                $scope.device= data;
                $scope.node_datetime = "Node Time"
                $scope.device_datetime = "Device Time"
                if("current_timestamp" in data){
                    $scope.device_timestamp = new Date(data.current_timestamp*1000);
                    $scope.device_datetime = $scope.device_timestamp.toUTCString();
                    $http.get('/node/timestamp').success(function(data_node){
                        node_t = data_node.timestamp;
                        node_time = new Date(node_t*1000);
                        $scope.node_datetime = node_time.toUTCString();
                        $scope.delta_t_min = (node_t - data.current_timestamp) / 60;
                     });
                }

                $scope.device.url_img = "/device/"+ $scope.device.id  + "/last_img" + '?' + Math.floor(new Date().getTime()/1000.0);
                $scope.device.url_stream = '/device/'+device_id+'/stream';

                //TODO: this needs to be fixed to point to local server upload!
                $scope.device.url_upload = "http://"+$scope.device.ip+":9000/upload/"+$scope.device.id ;

            //$scope.device.ip = device_ip;
                status = $scope.device.status
                if (typeof spStart != undefined){
                    if(status != 'initialising' && status !='stopping'){
                        spStart.stop();
                    }
                }
             });
        }
        }

        refresh_data = $interval(refresh, 3000); // miliseconds
        //clear interval when scope is destroyed
        $scope.$on("$destroy", function(){
        $interval.cancel(refresh_data);
        //clearInterval(refresh_data);
    });

    });

})()
