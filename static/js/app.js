$(document).ready(function () {
    'use strict';

    var active_markers = [];
    var all_markers = [];
    var movie_markers = {}; // Mapping from movie id to array of markers
    var location_marker = {}; // Mapping from place id to marker

    var $window = $(window);

    // Backbone
    var dispatcher = _.clone(Backbone.Events);

    var Location = Backbone.Model.extend({
        initialize: function (obj) {
            this.id = obj.identifier;
            this.marker = new google.maps.Marker({
                position: {lat: obj.lat, lng: obj.lng},
                map: map,
                icon: 'http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=' + (obj.idx + 1) + '|FE7569'
            });
            this.marker.idx = obj.idx + 1;

            if(movie_markers.hasOwnProperty(obj.movie_id)){
                movie_markers[obj.movie_id].push(this.marker);
            } else {
                movie_markers[obj.movie_id] = [this.marker];
            }
            location_marker[this.id] = this.marker;
            all_markers.push(this.marker);
        },
        destroy: function () {
            this.marker.setMap(null);
            delete this.marker;
            Backbone.Model.prototype.destroy.apply(this, arguments);
        }
    });

    var LocationList = Backbone.Collection.extend({
        fetchTimeout: null,
        delayedFetch: function () {
            clearTimeout(this.fetchTimeout);
            var that = this;
            this.fetchTimeout = setTimeout(function () {
                that.fetch({reset: true});
                that.fetchTimeout = null;
            }, 500);
        },
        model: Location,
        url: function () {
            return '/json/locations?bounds=' + map.getBounds().toUrlValue() + '&center=' + map.getCenter().toUrlValue();
        },
        reset: function () {
            this.each(function (model) {
                if(model && model.hasOwnProperty('destroy')){
                    model.destroy();
                }
            });
            active_markers = [];
            all_markers = [];
            movie_markers = {};
            location_marker = {};
            Backbone.Collection.prototype.reset.apply(this, arguments);
        }
    });

    var Locations = new LocationList;

    var LocationView = Backbone.View.extend({
        tagName: 'div',
        template: _.template($('#location-tile').html()),
        events: {
            'click .tile-poster': 'invokeMovieDetails',
            'click .tile-sview': 'updateState'
        },
        initialize: function () {
            this.listenTo(this.model, 'change', this.render);
            this.listenTo(this.model, 'destroy', this.remove);

            this.marker = this.model.marker;
            this.marker.view = this;
            var that = this;
            google.maps.event.addListener(this.marker, 'click', this.updateState.bind(this));

            dispatcher.on('ListView:scroll', this.setStreetView, this);
        },
        render: function () {
            var template_data = this.model.toJSON();
            template_data['street_view'] = '/static/img/streetview.png';
            this.$el.html(this.template(template_data));
            return this;
        },
        setStreetView: function(){
            if(this.isInView()){
                // To set street view iage only when scrolled into view
                var sview = 'https://maps.googleapis.com/maps/api/streetview?size=100x100&location=';
                sview += this.marker.getPosition().toUrlValue() + '&sensor=false';
                this.$el.find('img.tile-sview').attr('src', sview);
            }
        },
        isInView: function(){
            var docViewTop = $window.scrollTop();
            var docViewBottom = docViewTop + $window.height();

            var elemTop = this.$el.offset().top;
            var elemBottom = elemTop + this.$el.height();

            return ((elemTop <= docViewBottom) && (elemBottom >= docViewTop));
        },
        className: 'horizontal-tile grey groove',
        updateState: function(){
            if(this.marker.highlighted){
                this.nohighlight();
            } else {
                this.highlight();
            }
        },
        highlight: function(){
            this.marker.setIcon('http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=' + this.marker.idx + '|55ACEE');
            this.$el.children('.inner-tile').addClass('highlight');
            this.marker.highlighted = true;
            active_markers.push(this.marker);
        },
        nohighlight: function(){
            this.marker.setIcon('http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=' + this.marker.idx + '|FE7569');
            this.$el.children('.inner-tile').removeClass('highlight');
            this.marker.highlighted = false;
            var idx = [];
            for(var i=0; i<active_markers.length; i++){
                if(active_markers[i] == this.marker){
                    idx.push(i);
                }
            }
            for(i=0; i<idx.length; i++){
                active_markers.splice(idx[i], 1);
            }
        },
        invokeMovieDetails: function(){
            var movie_id = this.model.toJSON()['movie_id'];
            var movie = new Movie({id: movie_id});
            movie.fetch({
                success: function(){
                    var movieView = new MovieView({model: movie});
                    movieView.render();
                }
            });
        }
    });

    var LocationListView = Backbone.View.extend({
        el: $('#tiles'),
        list: [],
        initialize: function () {
            this.listenTo(Locations, 'add', this.addOne);
            this.listenTo(Locations, 'reset', this.addAll);
            this.listenTo(Locations, 'all', this.render);
        },
        events: {
            'scroll': 'triggerScroll'
        },
        addOne: function (location) {
            var view = new LocationView({model: location});
            this.$el.append(view.render().el);
            view.setStreetView();
            this.list.push(view);
        },
        addAll: function () {
            this.$el.empty();
            Locations.each(this.addOne, this);
        },
        triggerScroll: function(){
            dispatcher.trigger('ListView:scroll');
        }
    });

    var ListingView = new LocationListView;

    var Movie = Backbone.Model.extend({
        urlRoot: '/json/movie'
    });

    var MovieView = Backbone.View.extend({
        events: {
            'click .back': 'close'
        },
        el: $('#movie-details'),
        template: _.template($('#movie-template').html()),
        render: function(){
            updateMovieMarkers(this.model.id, true);
            this.$el.html(this.template(this.model.toJSON()));
            this.$el.show();
        },
        close: function(){
            updateMovieMarkers(this.model.id, false);
            this.$el.empty().hide();
        }
    });

    var SuggestionsView = Backbone.View.extend({
        el: $('#suggestions'),
        template: _.template($('#search-template').html()),
        fetchTimeout: null,
        events: {
            'click .movie.suggestion': 'highlightMovie',
            'click .location.suggestion': 'highlightLocation'
        },
        delayedFetch: function(){
            clearTimeout(this.fetchTimeout);
            var that = this;
            this.fetchTimeout = setTimeout(function () {
                that.suggest();
                that.fetchTimeout = null;
            }, 1000);
        },
        initialize: function(){
            dispatcher.on('Search:update', this.delayedFetch, this);
            this.$el.hide();
        },
        suggest: function(){
            var query = $('#search').val();
            var that = this;
            $.ajax({
                url:"/json/search",
                data: {q: query},
                success:function(result){
                    if(result.movies.length || result.locations.length){
                        that.$el.html(that.template(result));
                        that.$el.show();
                    } else {
                        that.$el.hide();
                    }
                }
            });
        },
        highlightMovie: function(ev){
            updateMovieMarkers(ev.currentTarget.id, true);
        },
        highlightLocation: function(ev){
            var m = Locations.get(ev.currentTarget.id);
            m.marker.view.updateState();
        }
    });

    var SearchView = Backbone.View.extend({
        el: $('#search'),
        events: {
            'keyup': 'keyupHandler'
        },
        keyupHandler: function(){
            dispatcher.trigger('Search:update');
        }
    });

    var Search = new SearchView;
    var Suggestions = new SuggestionsView;

    var City = Backbone.Model.extend({
        initialize: function(obj){
            this.id = obj.identifier;
            this.location = {
                lat: obj.lat,
                lng: obj.lng
            };
            this.name = obj.formatted_name;
        },
        select: function(){
            initializeMap({
                center: this.location,
                zoom: 15
            });
            $('#city-name').text(this.name);
        }
    });

    var CityList = Backbone.Collection.extend({
        model: City,
        url: function(){
            return '/json/cities';
        }
    });

    var Cities = new CityList;

    var CityListView = Backbone.View.extend({
        el: $('#city'),
        template: _.template($('#city-template').html()),
        initialize: function(){
            this.listenTo(Cities, 'reset', this.render);
        },
        events: {
            'change': 'select'
        },
        render: function(){
            this.$el.html(this.template({'cities': Cities.toJSON()}));
        },
        select: function(ev){
            this.changeCity(this.$el.val());
        },
        changeCity: function(city_id){
            var city = Cities.get(city_id);
            if(city){
                city.select();
            }
        }
    });

    var CityListing = new CityListView;
    Cities.fetch({
        reset: true,
        success: function(){
            Cities.first().select();
        }
    });

    function updateMovieMarkers(movie_id, highlight){
        if(!movie_markers.hasOwnProperty(movie_id)){
            return;
        }
        for(var i=0; i<movie_markers[movie_id].length; i++){
            if(highlight){
                movie_markers[movie_id][i].view.highlight();
            } else {
                movie_markers[movie_id][i].view.nohighlight();
            }
        }
    }

    function updateLocationMarker(location_id){
        var lm = location_marker[location_id];
        if(lm){
            lm.view.updateState();
        }
    }

    // Google Maps
    var map;

    function setMapWidth() {
        var mapWidth = window.innerWidth - 400;
        var mapDiv = document.getElementById('map-canvas');
        mapDiv.style.width = mapWidth + 'px';
    }

    function initializeMap(mapOptions) {
        map = new google.maps.Map(document.getElementById('map-canvas'), mapOptions);

        setMapWidth();
        google.maps.event.addDomListener(window, 'resize', setMapWidth);

        google.maps.event.addListener(map, 'bounds_changed', function () {
            Locations.delayedFetch();
        });
    }
});
