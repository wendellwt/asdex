<template>
  <div style="background-color: orange">

    <!-- ========== map & view ========= -->
    <vl-map  :load-tiles-while-animating="true"
             :load-tiles-while-interacting="true"
             data-projection="EPSG:4326"
             ref="map"
              @mounted="onMapMounted"
           >

    <vl-view ref="view"
             :zoom.sync="zoom"
             :center.sync="center"
             :rotation.sync="rotation"></vl-view>

      <!-- ========== layers ========= -->
      <!-- OpenStreetMap base layer
      -->
      <vl-layer-tile id="osm">
        <vl-source-osm></vl-source-osm>
      </vl-layer-tile>

      <!-- flight path features layer - geojson file retrieval via url
          TODO: swap out default url loader for custom loader (for error checking)
          almost: https://github.com/ghettovoice/vuelayers/issues/59
          uses style function/factory to color item based on geojson properties

      -->
      <vl-layer-vector >
        <vl-source-vector :url="geojsonUrl"
                          :features.sync="geojFeatures" />
        <vl-style-func :factory="geojStyleFuncFactory"></vl-style-func>
      </vl-layer-vector>

      <!-- kml features layer
      -->
      <vl-layer-vector >
          <vl-source-vector :url="kmlUrl"
                            :format-factory="kmlFormatFactory" />
      </vl-layer-vector>

      <!-- asdex layer ==========================  -->
      <vl-layer-vector >

        <vl-source-vector
                  :features.sync="asdexFeatures"
                  :url="asdexUrl"
                  :loader-factory="loaderFactory"
                  :update="aaaFeatures"
                  />
        <vl-style-func :factory="asdexStyleFuncFac" />

      </vl-layer-vector>

      <!-- ========== popup =========
          note: 'display' string in geojson properties was crafted by python
      -->
   <vl-interaction-select :features.sync="geojFeatures"></vl-interaction-select>

    <vl-overlay v-for="feature in geojFeatures"
                :key="feature.id"
                :position="feature.geometry.coordinates[0]">
      <div style="background: #ccf">
        {{ feature.properties.display }}
      </div>
    </vl-overlay>

      <!-- ========== end ========= -->
    </vl-map>

  </div>
</template>

<script>

// $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

import ZoomSlider from 'ol/control/ZoomSlider'
import ScaleLine  from 'ol/control/ScaleLine'
import Stroke     from 'ol/style/Stroke'
import Style      from 'ol/style/Style'
import KML        from 'ol/format/KML'

// ==========================================================

var global_asdexUrl = 'bogus';

const methods = {

    loaderFactory: (vm) => (extent, resolution, projection) => {
      // console.log("inside loaderFactory");

//nope: console.log(this.$refs.vectorSource.$source.getUrl());
//let my_url = this.$refs.vectorSource.$source.getUrl();
//console.log(my_url);
// undefined: console.log(vm.$source.getUrl());
console.log("this print is just for lint:", vm, extent, resolution, projection);

// =============== duplicate =================
      return fetch(global_asdexUrl)
        .then(response => response.json())
        .then(data =>  {
            // console.log("then(data)");
            // console.log(typeof data);

// =======================================
        let dlist = [];
        // ALL OF IT: data.features.length;
        for (let k = 0; k < 8; k++) {   // <<<<<<<<<<<< FIXED
            let elem = { track:  data.features[k].properties.id,
                         acid:   data.features[k].properties.acid,
                         actype: data.features[k].properties.actype  };
            dlist.push(elem);
        }
//this.$root.$emit('dlist', (dlist) );
// =============== duplicate =================

// console.log(dlist);
// console.log("++++ vm:");
// console.log(vm);
// console.log("++++ this:");
// console.log(this);
//console.log(this.$refs.data);
//console.log(this.$refs.data.asdexUrl);
//console.log(this.$refs.$data);
//console.log(this.$refs.$data.asdexUrl);
//console.log("++++");
        // this <<<<<<<< is not defined???
// app.$emit('dlist', (dlist) );

//console.log("after app.$emit");
        // =======================================
        return(data);
     })
   },

    onMapMounted () {
      // now ol.Map instance is ready and we can work with it directly
      this.$refs.map.$map.getControls().extend([
        new ScaleLine(),
        new ZoomSlider(),
      ])
    },

    kmlFormatFactory () {
      return new KML()
    },

    // ------------ ASDEX attempt to color lines
    asdexStyleFuncFac() {
      const activestyle = new Style({
          stroke: new Stroke({
            color: 'magenta',
            width: 3.25,
          })
      })

      return (feature) => {
        // help: using feature is pointless;
        // but what is an 'arrow function' with no args???
        if (feature.get('acid')) {
          return activestyle
        }
        return activestyle
     }
    },
    // ------------ attempt to color lines
    geojStyleFuncFactory() {
      const unkStyle = new Style({
          stroke: new Stroke({ color: 'brown', width: 3.25, })
      })

      return (feature) => {
        if (feature.get('SOURCE_TYPE')) {
          if (feature.get('SOURCE_TYPE')=='S') {
            return new Style({ stroke: new Stroke({ color: 'green', width: 3.25, }) })
          }
          if (feature.get('SOURCE_TYPE')=='F') {
            return new Style({ stroke: new Stroke({ color: 'blue', width: 3.25, }) })
          }
          if (feature.get('SOURCE_TYPE')=='A') {
            return new Style({ stroke: new Stroke({ color: 'magenta', width: 3.25, }) })
          }
          return unkStyle;
        }
        return unkStyle;
     }
   }
}

// ==========================================================

// center map on center of usa
var KSTL = [-90.3700289, 38.7486972];

export default {
    methods,
    data () {
      return {
        zoom: 5,
        center: KSTL,
        rotation: 0,

        geojsonUrl: '',
        geojFeatures: [],

        kmlUrl: '',

        asdexUrl: 'bogus',
        asdexFeatures: [],
        aaaFeatures: []   // rather old: https://github.com/ghettovoice/vuelayers/issues/25
      }
    },

// ==========================================================

  mounted () {

    // ---- receive vuejs message from AppUI, insert query into reactive
    // ---- location which apparently fires off a url request
    // -------------------------
    this.$root.$on('geojsonurl', (the_query) => {
      console.log("geojson:"+the_query);

      this.geojsonUrl = the_query;   // << that's all we have to do!
    })
    // -------------------------
    this.$root.$on('kmlurl', (the_query) => {
      console.log("kml:"+the_query);

      this.kmlUrl = the_query;
    })
    // -------------------------
    this.$root.$on('asdexurl', (the_query) => {
      console.log("asdex::"+the_query);

      // NOTE: loacerFactory does the actual retrieve
      global_asdexUrl = the_query;  // Q: is there a better way to communicate this???
      this.asdexUrl = the_query;
// =============== duplicate =================
      return fetch(global_asdexUrl)
        .then(response => response.json())
        .then(data =>  {
            console.log("then(data)");
            console.log(typeof data);
// =======================================
            let dlist = [];
            for (let k = 0; k < data.features.length; k++) {
                let elem = { track:  data.features[k].properties.id,
                             acid:   data.features[k].properties.acid,
                             actype: data.features[k].properties.actype  };
                dlist.push(elem);
            }
            this.$root.$emit('dlist', (dlist) );
// =============== duplicate =================
        })
// =============== duplicate =================
    })
  }, // ---- mounted

  watch: {
    // asdexFeatures: function (val) {
      // console.log("+++++++++++ watch on asdexFeatures:");
      // console.log(val);
      // console.log(this.asdexFeatures);
      // console.log(this.aaaFeatures);
      // console.log("+++++++++++ done with asdexFeatures");
    // },
    // aaaFeatures: function (val) {
      // console.log("watch on aaaFeatures:");
      // console.log(val);
    // },
    // asdexUrl: function (val) {
      // console.log("watch on asdexUrl:");
      // console.log(val);
    // }
  }
}

</script>

