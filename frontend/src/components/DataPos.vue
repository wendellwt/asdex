<template>
  <div class="datacolumn">

<h3>Data Position List</h3>
<div class="timestamp">{{last_rcvd}}</div>

<ul id="example-1" class="scrolling" >

  <li  class="datalist"
       v-for="item in datablocks"
       :key="item.track"
       @click="datablocklist(item)" >

    track: {{ item.track }}
    <br/>
    acid: {{ item.acid }}
    <br/>
    type: {{ item.actype }}
  </li>

</ul>

  </div>
</template>

<script>

export default {
    data () {
      return {
        last_rcvd: new Date(),

        datablocks : [
          { track: 1, acid: 'N111', actype: 'C172' },
          { track: 2, acid: 'N112', actype: 'C172' },
          { track: 3, acid: 'N113', actype: 'C172' },
          { track: 4, acid: 'N114', actype: 'C172' },
          { track: 5, acid: 'N115', actype: 'C172' } ]
      }
    },

  mounted () {

      this.$root.$on('dlist', (dlist) => {
      console.log("DataPos received dlist");

      // FIXME: find out how/why PostGIS allowed duplicate track
      // why do we need to do this here?: remove duplicate key / track

      this.datablocks = this.removeDuplicates(dlist, 'track');
    })
  },

  methods: {

 // =========================
 // https://firstclassjs.com/remove-duplicate-objects-from-javascript-array-how-to-performance-comparison/
 removeDuplicates: function(array, key) {
    return array.filter((obj, index, self) =>
        index === self.findIndex((el) => (
            el[key] === obj[key]
        ))
    )
},
// =========================

      datablocklist: function(item) {
          //console.log("datablocklist");
          //console.log(item);
          // console.log(item.key); // undefined
          console.log("highlightthis-emit:" + item.track + ":" + item.acid + "_" + item.actype);
          this.$root.$emit('highlightthis', (item.track) );
      }
  }
}

</script>

<style lang="scss">
/* https://www.w3schools.com/css/default.asp */

div.datacolumn {
    background-color: #ffecb3;
}

div.timestamp {
  font-size: 70%;
}

li.datalist {
    border-style: solid;
    border-color: black;
    background-color: #e6ffcc;

    margin-top: 5px;
    margin-bottom: 5px;
}

ul.scrolling {
        max-height: 400px;
        overflow: scroll;
}

</style>

